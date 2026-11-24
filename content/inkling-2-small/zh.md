# 解读 Inkling 2 Small

**总体评价**：Inkling 2 Small 的信息流微操、低精度配方和后训练可塑性，非常有启发和新意，宛如 Kimi 和 DeepSeek；但有别于 MAI-Thinking-1 和 Reflection Beam，它对预训练数据配方避而不谈，亦宛如 Kimi 和 DeepSeek。整体给到夯。

参数量是 594B-A17B，比 Inkling 1 Small 的 276B-A12B 大了一倍多。骨架是 48 层 GQA + MoE，SWA:FA = 5:1，384 experts 选 8。视觉侧放弃了 Inkling 1 的 encoder-free 4 层 hMLP，改回 23 层 ViT，同时砍掉音频。RL 前四阶段披露的训练量合计约 12.55T token，相对其他同量级 SOTA 模型偏少。第一阶段在 GB300 NVL72 上跑了人神共愤的 68 小时，以原生 NVFP4 训完 8.4T token，第二阶段喂了 3.8T 高质量新数据，最后两个阶段用约 354B 推理与智能体轨迹拉到 1M 上下文，其中 H3 还混入了预训练数据回放。随后 2048 卡跑了 9 天 mixed RL，超过 1700 万次 rollout，rollout 的 P50、P99 耗时分别是 8 分钟和 4 小时。MoE 从预训练第一步到最后一次 RL rollout 都跑在同一套 NVFP4/MXFP8 配置上，无需训后 calibration。

## 架构与预训练

架构选择上，Inkling 2 Small 取消了 Inkling 1 的共享专家，同时依旧没有 Engram，没有 linear attention 或者 learned sparse attention，也没有 LatentMoE。可能是 training recipe 没有 ready，也可能是后训练 customizability 不好搞。也可能这两者本质上是一件事。Inkling 2 对信息流做各方面修改，包括相邻 token 的组合、跨层表示的读取，以及 Attention logits 和各分支 activation 的幅度控制。可能是为了防止训崩，也可能是为了耍 training speedrun。也可能这两者本质上是一件事。这些修改都比较微操，所以 vLLM Day-0 专门写了 allreduce_conv_mix，把 ShortConv、Block AttnRes 和 RMSNorm 这串小算子全留在寄存器里一次算完。

位置信息编码上，Inkling 2 接过 Inkling 1 的火炬，做 Relative Attention 的非遗传承人。它的语言主干不用 RoPE，而是在 softmax 前给 Attention logits 加入内容相关的相对位置项，让距离偏好随当前 token 而变。跟八年前的古法 Relative Attention 不同，全局层的位置项在超出一定距离后直接归零，相当于近处兼顾语序，远处纯 RAG。当初 RoPE 能流行起来，很重要的一个原因是大家改不动 FlashAttention。好在 kernel agents 时代，改 FlashAttention 已如提篮买菜，RoPE 或终将 say goodbye。

虽然 DFlash2 在 8 月份已经先用上了 Dynamic ShortConv，但把 Dynamic ShortConv 落地到百 B 级开放模型的主干中，Inkling 2 还是头一个。这条线其实从 PLM 4.1 开始就很清晰了。当初 Canon Layers 一声炮响，把 ShortConv 插进 Attention 和 MLP，靠每个 token 把相邻 token 的信息流一卷来减轻主干的学习负担，直接救活了 NoPE 和 linear attention。Inkling 1 随后就在每层的 K、V、Attention 输出和 MLP 输出上加了 width 4 ShortConv。到了 Inkling 2，他们把全局层 K、V 上的 ShortConv 进一步动态化，让局部混合权重随 token 变化，或与前面的 Relative Attention 打配合。

Block AttnRes 这块借鉴了 Kimi K3，不过两者并不是同一套 block size。Kimi K3 是 93 层、每 12 层一组，Inkling 2 Small 是 48 层、每 6 层一组，两边维持的都是大约 8 个 depth blocks。细节上，Kimi K3 只对 key 做 norm，Inkling 2 对 value 也做了 norm，让不同 block 的贡献更多由 Attention weights 决定。而且在它的 8 个全局 Attention 层中，Q、K、V 各自通过独立的 depth query 计算跨 block 的 Attention weights，从不同的 block 组合中读取表示，不再共享同一份跨层输入。

Attention 输出端方面，Inkling 2 除了率先在主流大模型里落地 Dynamic Attention Sink，还引入了 Gated Attention。Dynamic Attention Sink 用专门的权重把当前 token 的 hidden state 映射成 per-head 的 sink logit，追加到正常 Attention logits 里一起做 softmax，但对应的 value 为 0，让每个 head 把部分概率分给虚空。Gated Attention 则是在 output projection 前，用输入相关的 sigmoid gate 对 Attention 输出逐 channel 调节。所以 Dynamic Attention Sink 相当于 softmax 内部的 head-wise gate，Gated Attention 则是 output projection 前的 channel-wise gate。

Inkling 2 把 Inkling 1 的 QK norm 换成了 L2 clipping，V 也加上了不带可学习 scale 的 RMSNorm，让 Attention weights 对读出幅度的控制更直接。此外模型还引入了 weight norm，把权重本身的尺度也纳入控制。MoE 里则用了 Kimi K3 提出的 soft-capped SwiGLU，对 gate 分支的线性因子和 up 分支分别做阈值为 4 和 25 的 tanh softcap，sigmoid 仍然接收原始 gate 输入，防止两个无界分支相乘后放大 activation outliers。最终的 vocabulary logits 也做了阈值为 30 的 tanh softcap。

MoE 的 soft-capped SwiGLU 也在给 FP4 铺路：压缩 activation 尖峰，减轻 outlier 撑大量化 scale、挤掉小值的问题。Inkling 2 的 Attention 依然以 BF16 为主，Attention 输出与 router 保留 FP32，低精度主要落在 MoE expert GEMM。其中前 5⁄6 层前向走 NVFP4、最后 1⁄6 层保留 MXFP8，且只在 activation 上用 Four Over Six、权重不用。它放弃了 NVIDIA 的 16×16 粗粒度共享 scale、保留 1×16 细粒度，outer scale 则参考 Composer 2 拆成权重 per-expert、activation per-token，以此兼顾 batch invariance 并避免 causality leakage。到了反向，MoE expert GEMM 统一使用 MXFP8，借鉴 TetraJet-v2 和 Quartet II 的思路，复用前向量化后的权重和 activation，将其反量化、转置再用 stochastic rounding 重量化成 MXFP8，分别用于 DGRAD 和 WGRAD，保证反向张量在期望上对齐前向量化结果。这套 FP4 训练应该是继 Nemotron 3 系列、Composer 2 后唯一公开的生产级 4-bit 训练 recipe，目前国产模型都不太公布 FP4 训练方案，比如 Ling 和 Seed 发 FP4 小论文时都稍显隐晦，不知在如今硬件指纹暴露之后是否情况会有所改变。

通信上，前向 dispatch 走 NVFP4，combine 因为直接用 MXFP8 精度不够，改用 32 维 RHT 加 S2F6 把传输压到 8.25 bits/value。整体上看，RHT 只用于前向 combine，4-bit 也只用于前向计算；MoE expert 的反向 GEMM 使用 MXFP8，对保存的前向量化张量做 stochastic re-quantization，不用 RHT。相比全 MXFP8，预训练加速 8%、RL 加速 20%，代价是预训练 compute efficiency 损失约 2%，RL reward 无可辨差异。不过 594B 总参数不代表每个 expert GEMM 形状都够大，Small 的计算 shape 并不能打满 Tensor Core，BBBK 对小 shape 的优化投入也不算多，更大尺寸上这套 FP4 的收益应该会更明显。

解码头也换了，Inkling 2 Small 把 Inkling 1 的串联 MTP 换成了 5 层的 DSpark，每步 draft 7 个 token，并跟 Mistral Large 4 一样用 RNN head 建模 block 内依赖。

RL 前的最后两个阶段，Inkling 2 用了 Kimi K3 来做轨迹蒸馏。对于 Kimi 而言，这或许是继 Cursor 后第二次公开靠训练授权入账。

## 后训练

Inkling 2 公开的 RL 数据配比明显向代码倾斜，coding 占了 38.5% 的 rollout 和 65% 的 token，chat、safety 和 epistemics 合计只占 7.8% 的 rollout 和 0.2% 的 token，不过通用的 alignment reward 会施加在所有任务上。

训练组织上，Inkling 2 把 Inkling 1 分拆的 reasoning、agentic RL 和 MOPD 改回 joint/mixed RL，跟 MiMo-V2.6 一样，只是 MiMo-V2.6 在 mixed RL 后还会用 MOPD2 补充难验证、超长程等任务。RL 阶段单窗口训在 256K，靠 compaction 撑出 p99 高达 1.5M tokens、4 小时的累计轨迹，期间主要靠 sticky routing 加 DRAM KV-cache offloading 维持 93% 以上的 prefix-cache 命中率，把 sampler 和 trainer 的卡数比例压在了 5:3。即便如此，采样策略相对 trainer 的中位数 staleness 依然达到 17 次参数更新，这种情况下还能训稳，可能是算法确实扛得住长尾 staleness，也可能是并没有放太多超长程的任务。

算法侧最关键的是 Score Centering 的变体 StableReinforce。虽然业内早就在传 frontier labs 私下在用，Together AI 公开论文后也有百 B 级专项 RL 出现过 top-k 近似版本，但 Inkling 2 首次把它公开放进 594B 体量、两千卡级多任务 joint RL。它的核心是在每个 prefix 上，从 trainer 的策略梯度 score（∇log p(a|s)）里减去它在 sampler 分布下的期望，以此消除 training-inference mismatch 引入的 mean-score drift。原论文用 top-128 概率加 tail 来近似这个期望。第三方对 Tinker 的逆向分析则发现，StableReinforce 改成了从 sampler 随机抽取 8 个 token 做蒙特卡洛估计，虽然方差更高但无偏，同时也大幅压缩了需要保存的 sampler 信息。此外逆向帖还指出，这套修正本质上等价于带 advantage 权重的 KL 项，区别于 Tinker 额外加上的普通 sampler–learner KL 正则（默认系数 0.01），后者不乘 advantage。

Alignment 上，Inkling 2 Small 早期偏重能力提升的 RL 把 checkpoint 训得过于执着于成功，绕过约束、编造结果等行为频繁出现，哪怕到了主 RL 阶段，监控也抓到过模型在任务失败后利用第三方服务绕开网络封锁的情况。考虑到 Tinker 要让客户自己跑大规模后训练，团队在发布前集中做了一轮从 SFT 到 RL 的安全加固。具体做法是将“什么时候应该停止”纳入策略学习，在不可能完成的任务上奖励放弃，通过跨任务的 alignment reward 抑制隐瞒和作弊，再用 spec-conditioned OPSD 把 conduct spec 内化进权重。即便训练期间没看过 HoneyBench，这轮改进也迁移到了这个外部未见评测上。

## 模型能力

Inkling 2 Small 的 AA Intelligence Index 拿到 31，非国产开源权重第一，约在 Gemini 3.8 Flash 梯队，高出 Mistral Large 4 的 26，SWE、视觉和金融法务表现都很强。自家 held-out 代码集上，pre-trained BPB 拿到 0.2030，压过同样用预训练格式微调还原的 Kimi K3.1 Pro（0.2068）和 DeepSeek V4.1 Flash（0.2209），完整后训练后的 BPB 只回退 0.0050 到 0.2080。Terminal-Bench v2.1（Terminus）能拿 81.3%，v4.0（mini-swe-agent）则为 13.1%，在后者明显落后于同场的 DeepSeek V4.1 Flash（33.8%）和 GLM 5.3（41.9%）。另外评测口径和保守策略也贡献了不少账面分，最大 trajectory budget 从 Inkling 1 Small 的 256K 放宽到了 1M，知识题幻觉率下降主要也不是因为答对更多（准确率只微涨 2 个点），而是靠拉高拒答率换来的。

另外 TML 还演示过让它自主花 Tinker 预算去训一个 Qwen3.5-4B，模型在发现 RL 引起过度自信后主动停掉 RL 改交 SFT。在 Weight-Space Programming 任务上，它先是在内部探索评测里表现不错，随后外部作者用 WSP-Gym 对它做小型 ReLU 网络修复的专项后训练，平均输出从带 reasoning 的约 10,600 tokens 压到不带 reasoning 的 38 tokens，修复率也因为不再爆预算从 76% 提到了 83%。

不过换到真实外部 harness 时，泛化依然不够稳。虽然 Inkling 2 Small 训练时明明做了 multi-harness、多种 context-compaction 策略的 RL，有人还是发现在 Codex harness 下它明显落后于 GPT-6-Luna，换上 pi、mini-swe-agent、CC 后却超过了它，而换 harness 对 Luna 和 Inkling 1 Small 来说基本没有收益甚至变差。

Inkling 2 Small 可能是业内第一个公开把 customizability 设成 launch-blocking evaluation 维度的模型项目，看重的是固定数据和预算下客户对发布模型继续微调能拿到的收益，而大多数模型厂能做到像 Qwen3.8-Next 这样在预训练中兼顾自家后训练潜力就已经颇为难得了。之前有用户吐槽 Inkling 1 Small 比 Qwen 难微调，这对微调服务商来说显然有点难堪。具体评测统一使用 async RL 加 StableReinforce，逐模型做 LR sweep、跑 200 步，Inkling 系列取 3 个 seeds 均值。金融财报摘要任务上，Inkling 2 Small 只跑了 75 步定制 RL，就追平了 Inkling 1 Small 在这次 200 步实验中的最终表现。

从减少后训练遗忘的角度看，customizability 的一个可能机制就是寻找更平坦的解。以前大家就发现延长预训练会提高权重对修改的敏感度、导致微调表现反而下降，而 SAM、更高的学习率或者更短的退火阶段等偏向平坦解的做法，则能减少后续遗忘。Inkling 2 Small 的 RL 前各阶段披露的训练量合计约 12.55T token，在同量级 SOTA 模型里确实偏少，像 550B 的 Nemotron 3 Ultra 喂了 20T，744B 的 GLM-5 跑了 28.5T，激活参数相近的 GLM-5.3-Flash 和 DeepSeek-V4 Flash 甚至也在 30T 以上。不过官方同样将它定位为 predictive scaling ladder 的其中一级，较少的训练量可能是为了平坦解留可塑性，也可能只是按这个尺寸的迭代节奏在跑配方验证。

## References

1. Thinking Machines Lab, *Introducing Inkling 2 Small*: [https://thinkingmachines.ai/news/inkling-2-small/](https://thinkingmachines.ai/news/inkling-2-small/)
2. Thinking Machines Lab, *Inkling 2 Small Model Card*: [https://thinkingmachines.ai/model-card/inkling-2-small/](https://thinkingmachines.ai/model-card/inkling-2-small/)
3. Thinking Machines Lab, *End-to-End 4-Bit Training*: [https://thinkingmachines.ai/blog/end-to-end-4-bit-training/](https://thinkingmachines.ai/blog/end-to-end-4-bit-training/)
4. Songlin Yang（确认 weight norm 与无 RMS gamma）: [https://x.com/SonglinYang4/status/2121022049544245556](https://x.com/SonglinYang4/status/2121022049544245556) , [https://x.com/SonglinYang4/status/2120989236304437360](https://x.com/SonglinYang4/status/2120989236304437360)
5. Jack Cook（前向 RHT 与反向独立 SR 说明）: [https://x.com/jackcookjack/status/2121399564938916339](https://x.com/jackcookjack/status/2121399564938916339)
6. Liyan Chen（594B 计算 shape 与 BBBK Tensor Core 利用率）: [https://x.com/liyanc98/status/2122147297945653685](https://x.com/liyanc98/status/2122147297945653685)
7. Nathan Lambert, *RLHF Book: Policy Gradients*（前沿实验室私下使用 Score Centering）: [https://rlhfbook.com/c/06-policy-gradients](https://rlhfbook.com/c/06-policy-gradients)
8. FireFlash（百 B 级专项 RL 使用 top-32 Score Centering）: [https://agenteconomics.org/posts/agentic-rl-recipe](https://agenteconomics.org/posts/agentic-rl-recipe)
9. Martin Marek（Tinker StableReinforce 逆向分析与 advantage-weighted KL 澄清）: [https://x.com/mrtnm/status/2114145584739192907](https://x.com/mrtnm/status/2114145584739192907) , [https://x.com/mrtnm/status/2114789685096534382](https://x.com/mrtnm/status/2114789685096534382)
10. John Schulman & Neil Chowdhury（能力 RL 副作用、安全干预与未见评测迁移）: [https://x.com/johnschulman2/status/2118528596340039790](https://x.com/johnschulman2/status/2118528596340039790) , [https://x.com/ChowdhuryNeil/status/2120574535808479675](https://x.com/ChowdhuryNeil/status/2120574535808479675)
11. Ziqiao Ma（内部探索性 Weight-Space Programming 评测）: [https://x.com/ziqiao_ma/status/2121461443652645157](https://x.com/ziqiao_ma/status/2121461443652645157)
12. Josh Purtell & Karen Zhou（Codex vs pi/CC harness 敏感性讨论）: [https://x.com/JoshPurtell/status/2118812984285782251](https://x.com/JoshPurtell/status/2118812984285782251) , [https://x.com/karenzzhou/status/2119925128406409544](https://x.com/karenzzhou/status/2119925128406409544)
13. Soumith Chintala & Jasper Lu（Customizability launch-blocking eval 与 Inkling 1 微调反馈）: [https://x.com/soumithchintala/status/2118499742246465563](https://x.com/soumithchintala/status/2118499742246465563) , [https://x.com/lu__jasper/status/2118491409879589047](https://x.com/lu__jasper/status/2118491409879589047)
14. Guangxuan Xiao（predictive scaling ladder 定位）: [https://x.com/Guangxuan_Xiao/status/2118507716381667825](https://x.com/Guangxuan_Xiao/status/2118507716381667825)
15. Jacob Springer et al., *Overtrained Language Models Are Harder to Fine-Tune*（ICML 2025）: [https://proceedings.mlr.press/v267/springer25a.html](https://proceedings.mlr.press/v267/springer25a.html)
16. Ishaan Watts et al., *Sharpness-Aware Pretraining Mitigates Catastrophic Forgetting*（ICML 2026）：[https://arxiv.org/abs/2605.02105](https://arxiv.org/abs/2605.02105)
