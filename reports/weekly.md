# modelagency weekly update

Source: BenchLM.ai (https://benchlm.ai), retrieved 2026-09-11; leaderboard and benchmark values remain attributed to BenchLM.ai and the original benchmark publishers.

[BenchLM dataset and license](https://benchlm.ai/data). BenchLM-backed quality signals are used when published; modelagency derives the documented fallbacks and value views.

## BenchLM source metrics

| Model | Agentic | Terminal-Bench 2.0 | BrowseComp | OSWorld-Verified | Overall |
| --- | ---: | ---: | ---: | ---: | ---: |
| [GPT-5.6 Sol](https://benchlm.ai/models/gpt-5-6-sol) | 92 (#1) | 91.9 | 92.2 | — | 80.63 (#5) |
| [GPT-6 Astra](https://benchlm.ai/models/gpt-6-astra) | 91.5 (#2) | — | 91.5 | — | 84.08 (#2) |
| [Claude Opus 5](https://benchlm.ai/models/claude-opus-5) | 90.8 (#3) | — | 90.8 | — | 81.97 (#3) |
| [Claude Fable 5](https://benchlm.ai/models/claude-fable-5) | 84.6 (#11) | 84.3 | — | 85 | 81.43 (#4) |
| [Claude Mythos 5](https://benchlm.ai/models/claude-mythos-5) | 87.1 (#8) | 88 | 88 | 85 | — (#—) |
| [GPT-5.6 Terra](https://benchlm.ai/models/gpt-5-6-terra) | 87.4 (#7) | 87.4 | 87.5 | — | 71.13 (#11) |
| [GPT-5.6 Luna](https://benchlm.ai/models/gpt-5-6-luna) | 84.1 (#13) | 84.7 | 83.3 | — | 64.65 (#38) |
| [Gemini 3.6 Flash](https://benchlm.ai/models/gemini-3-6-flash) | 83 (#16) | — | — | 83 | 68.39 (#23) |
| [Claude Sonnet 5](https://benchlm.ai/models/claude-sonnet-5) | 82 (#19) | 80.4 | 84.7 | 81.2 | 69.84 (#18) |
| [Claude Opus 4.8](https://benchlm.ai/models/claude-opus-4-8) | 80.4 (#23) | 74.6 | 84.3 | 83.4 | 72.22 (#8) |
| [Grok 4.6](https://benchlm.ai/models/grok-4-6) | — (#—) | — | — | — | 70.08 (#16) |

Retrieved 2026-09-11; source verified 2026-09-10.

BenchLM published ranks, overall scores, and verification lanes are unavailable in this snapshot. [View the canonical leaderboard](https://benchlm.ai/llm-agent-benchmarks).

## Default workload mix

| Share | Tier | Model | Quality signal | Allocated estimate |
| ---: | --- | --- | ---: | ---: |
| 10% | Specialist work | Claude Mythos 5 | 87.1 (BenchLM agentic score) | $45.00 |
| 30% | Everyday work | GPT-5.6 Terra | 71.1 (BenchLM overall score) | $37.50 |
| 60% | High-volume work | GPT-5.6 Luna | 64.7 (BenchLM overall score) | $30.00 |

Estimated allocation: $112.50/month; remaining budget: $187.50.

## Daily Driver · source-backed / derived fallback

- **Best Quality**: [GPT-5.6 Sol](https://benchlm.ai/models/gpt-5-6-sol) — 92.0 BenchLM source score / 100; token-price proxy $5/$30 per 1M in/out; [BenchLM agentic score](https://benchlm.ai/llm-agent-benchmarks)
- **Best Value**: [GPT-5.6 Luna](https://benchlm.ai/models/gpt-5-6-luna) — 84.1 BenchLM source score / 100; token-price proxy $1/$6 per 1M in/out; [BenchLM agentic score](https://benchlm.ai/llm-agent-benchmarks)
- **Lowest Token Price**: [GPT-5.6 Luna](https://benchlm.ai/models/gpt-5-6-luna) — 84.1 BenchLM source score / 100; token-price proxy $1/$6 per 1M in/out; [BenchLM agentic score](https://benchlm.ai/llm-agent-benchmarks)

## Engineering · source-backed / derived fallback

- **Best Quality**: [Claude Mythos 5.1](https://benchlm.ai/models/claude-mythos-5-1) — 100.0 derived index / 100; [benchlm](https://benchlm.ai/benchmarks/terminal-bench-4); [original benchmark](https://www.tbench.ai/news/terminal-bench-4-0)
- **Best Value**: [GPT-5.6 Luna](https://benchlm.ai/models/gpt-5-6-luna) — 84.7 BenchLM source score / 100; token-price proxy $1/$6 per 1M in/out; [BenchLM Terminal-Bench 2.0](https://benchlm.ai/benchmarks/terminal-bench-2); [original benchmark](https://arxiv.org/abs/2509.16941)
- **Lowest Token Price**: [Gemini 3.8 Flash](https://benchlm.ai/models/gemini-3-8-flash) — 50.0 derived index / 100; token-price proxy $0.75/$3.75 per 1M in/out; [benchlm](https://benchlm.ai/benchmarks/terminalbench21); [original benchmark](https://api-docs.deepseek.com/zh-cn/updates/)

## Management · source-backed / derived fallback

- **Best Quality**: [GPT-5.6 Sol](https://benchlm.ai/models/gpt-5-6-sol) — 92.2 BenchLM source score / 100; token-price proxy $5/$30 per 1M in/out; [BenchLM BrowseComp](https://benchlm.ai/benchmarks/browsecomp); [original benchmark](https://openai.com/index/browsecomp/)
- **Best Value**: [Gemini 3.8 Flash](https://benchlm.ai/models/gemini-3-8-flash) — 70.0 derived index / 100; token-price proxy $0.75/$3.75 per 1M in/out; [benchlm](https://benchlm.ai/benchmarks/osworld2); [original benchmark](https://arxiv.org/abs/2606.29537)
- **Lowest Token Price**: [Gemini 3.8 Flash](https://benchlm.ai/models/gemini-3-8-flash) — 70.0 derived index / 100; token-price proxy $0.75/$3.75 per 1M in/out; [benchlm](https://benchlm.ai/benchmarks/osworld2); [original benchmark](https://arxiv.org/abs/2606.29537)

## Media · source-backed / derived fallback

- **Best Quality**: [GPT-5.6 Sol](https://benchlm.ai/models/gpt-5-6-sol) — 100.0 derived index / 100; token-price proxy $5/$30 per 1M in/out; [benchlm](https://benchlm.ai/benchmarks/mmmu-pro); [original benchmark](https://arxiv.org/abs/2409.02813)
- **Best Value**: [Gemini 3.7 Flash](https://benchlm.ai/models/gemini-3-7-flash) — 81.8 derived index / 100; token-price proxy $0.75/$3.75 per 1M in/out; [benchlm](https://benchlm.ai/benchmarks/designarenawebsite); [original benchmark](https://openrouter.ai/x-ai/grok-4.3/benchmarks)
- **Lowest Token Price**: [Gemini 3.7 Flash](https://benchlm.ai/models/gemini-3-7-flash) — 81.8 derived index / 100; token-price proxy $0.75/$3.75 per 1M in/out; [benchlm](https://benchlm.ai/benchmarks/designarenawebsite); [original benchmark](https://openrouter.ai/x-ai/grok-4.3/benchmarks)
