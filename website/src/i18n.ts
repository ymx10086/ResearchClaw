export type Lang = "zh" | "en";

export const i18n: Record<Lang, Record<string, string>> = {
  zh: {
    "nav.docs": "文档",
    "nav.github": "GitHub",
    "nav.lang": "EN",
    "hero.slogan": "本地优先的 Research OS",
    "hero.sub":
      "把 project、workflow、claim、evidence、experiment 和 blocker 放进同一套运行时里，持续推进而不是只回答问题。",
    "hero.cta": "查看文档",
    "brandstory.title": "Why ResearchClaw？",
    "brandstory.para1":
      "ResearchClaw 取自 Research（科研）和 Claw（利爪），寓意为你的科研之路披荆斩棘、深入挖掘。",
    "brandstory.para2":
      "它不只是一个会回答问题的助手，而是一套把论文、工作流、实验、证据链和主动提醒放到一起的 Research OS。",
    "features.title": "核心能力",
    "features.papers.title": "研究项目与工作流",
    "features.papers.desc":
      "持久化 project、workflow、stage、task、artifact 与 binding，而不是只有一次性对话。",
    "features.references.title": "Claim 与证据图",
    "features.references.desc":
      "把论文、PDF chunk、note、citation、experiment 和生成 artifact 连接成可追溯证据链。",
    "features.analysis.title": "实验执行与结果接回",
    "features.analysis.desc":
      "记录 run、metrics、outputs、contracts、result bundles，并把结果自动挂回 workflow。",
    "features.channels.title": "Blocker 与主动推进",
    "features.channels.desc":
      "发现 contract gap、生成 remediation task、主动提醒，并支持批量 dispatch / execute / resume。",
    "features.skills.title": "结构化研究工具层",
    "features.skills.desc":
      "通过 Skills、API、Console 把 projects、notes、claims、experiments 和 remediation 暴露给 agent。",
    "features.private.title": "本地优先，可自托管",
    "features.private.desc":
      "研究状态、论文、实验和笔记都在你的 workspace 中，密钥与运行数据分离。",
    "testimonials.title": "社区怎么说",
    "testimonials.viewAll": "查看全部",
    "usecases.title": "你可以用 ResearchClaw 做什么",
    "usecases.sub": "",
    "usecases.category.literature": "文献闭环",
    "usecases.category.writing": "写作与沉淀",
    "usecases.category.experiment": "实验执行",
    "usecases.category.tracking": "健康度与阻塞",
    "usecases.category.collaboration": "频道与回传",
    "usecases.category.explore": "API 与扩展",
    "usecases.literature.1":
      "检索和跟踪 ArXiv、Semantic Scholar 的论文，把结果写入 project/workflow，而不是只返回一段聊天文本。",
    "usecases.literature.2":
      "阅读论文、生成 paper note、沉淀 note synthesis 和 hypothesis queue。",
    "usecases.literature.3": "把结论连接到 claim/evidence graph，追溯到 paper、note、experiment 和 artifact。",
    "usecases.writing.1":
      "把前期调研和实验结果沉淀成 writing task、draft artifact 和 review/follow-up 阶段。",
    "usecases.writing.2":
      "用 decision log、writing note 和 claim 状态来持续推进写作，而不是每次从零开始。",
    "usecases.experiment.1":
      "规划 baseline / ablation / stress runs，记录参数、输入、输出、metrics 和 result bundle。",
    "usecases.experiment.2": "接回 command、notebook、external execution 的结果，并触发 contract validation。",
    "usecases.tracking.1":
      "在 project dashboard 里查看 execution health、recent blockers、overdue remediation 和 ready-to-retry workflow。",
    "usecases.tracking.2": "直接批量派发、批量执行 remediation task，或恢复可重试的 workflow。",
    "usecases.collaboration.1":
      "通过 Console 和消息通道回传 blocker、paper watch、写作待办和研究进展。",
    "usecases.explore.1": "用 `/api/research/*` 和 `research_workflows` skill 组织你自己的长期研究自动化。",
    "quickstart.title": "快速开始",
    "quickstart.hintBefore": "安装 → 初始化 → 启动；部署与运维说明见 ",
    "quickstart.hintLink": "文档",
    "quickstart.hintAfter": "。",
    "quickstart.optionPip": "源码安装",
    "quickstart.badgeRecommended": "推荐",
    "quickstart.badgeBeta": "Beta",
    "quickstart.optionLocal": "本地安装",
    "quickstart.tabPip": "源码安装 (推荐)",
    "quickstart.tabPipMain": "源码安装",
    "quickstart.tabPipSub": "(推荐)",
    "quickstart.tabUnix": "macOS / Linux (Beta)",
    "quickstart.tabUnixMain": "macOS / Linux",
    "quickstart.tabUnixSub": "(Beta)",
    "quickstart.tabWindows": "Windows (Beta)",
    "quickstart.tabWindowsMain": "Windows",
    "quickstart.tabWindowsSub": "(Beta)",
    "quickstart.tabDocker": "Docker",
    "quickstart.tabDockerShort": "Docker",
    "quickstart.optionDocker": "Docker 镜像",
    "quickstart.tabPipShort": "Source",
    "quickstart.tabUnixShort": "Mac/Linux",
    "quickstart.tabWindowsShort": "Windows",
    footer: "ResearchClaw — 本地优先的 Research OS",
    "footer.builtWith": "基于 Python + FastAPI 构建",
    "docs.backToTop": "返回顶部",
    "docs.copy": "复制",
    "docs.copied": "已复制",
    "docs.searchPlaceholder": "搜索文档",
    "docs.searchLoading": "加载中…",
    "docs.searchNoResults": "无结果",
    "docs.searchResultsTitle": "搜索结果",
    "docs.searchResultsTitleEmpty": "搜索文档",
    "docs.searchHint": "在左侧输入关键词后按回车搜索。",
  },
  en: {
    "nav.docs": "Docs",
    "nav.github": "GitHub",
    "nav.lang": "中文",
    "hero.slogan": "Local-first Research OS",
    "hero.sub":
      "Keep projects, workflows, claims, evidence, experiments, and blockers in one runtime that keeps moving instead of only answering prompts.",
    "hero.cta": "Read the docs",
    "brandstory.title": "Why ResearchClaw?",
    "brandstory.para1":
      "ResearchClaw combines Research and Claw — a sharp tool that digs deep into academic knowledge on your behalf.",
    "brandstory.para2":
      "It is not only an assistant that answers prompts. It is a Research OS that keeps papers, workflows, experiments, evidence, and proactive follow-up in one runtime.",
    "features.title": "Key capabilities",
    "features.papers.title": "Research projects & workflows",
    "features.papers.desc":
      "Persist projects, workflows, stages, tasks, artifacts, and bindings instead of relying on one-shot chat state.",
    "features.references.title": "Claim & evidence graph",
    "features.references.desc":
      "Link papers, PDF chunks, notes, citations, experiments, and generated artifacts into a traceable graph.",
    "features.analysis.title": "Experiment execution & ingestion",
    "features.analysis.desc":
      "Track runs, metrics, outputs, contracts, and result bundles, then attach them back to the workflow.",
    "features.channels.title": "Blockers & proactive follow-up",
    "features.channels.desc":
      "Detect contract gaps, create remediation tasks, and batch dispatch, execute, or resume blocker handling.",
    "features.skills.title": "Structured research tooling",
    "features.skills.desc":
      "Expose projects, notes, claims, experiments, and remediation through skills, APIs, and the console.",
    "features.private.title": "Local-first, self-hosted",
    "features.private.desc":
      "State, papers, experiments, and notes stay in your workspace, with secrets stored separately.",
    "testimonials.title": "What people say",
    "testimonials.viewAll": "View all",
    "usecases.title": "What you can do with ResearchClaw",
    "usecases.sub": "",
    "usecases.category.literature": "Literature loop",
    "usecases.category.writing": "Writing & synthesis",
    "usecases.category.experiment": "Experiment execution",
    "usecases.category.tracking": "Health & blockers",
    "usecases.category.collaboration": "Channels & delivery",
    "usecases.category.explore": "APIs & extensions",
    "usecases.literature.1":
      "Search and track ArXiv and Semantic Scholar papers, but write the results into projects and workflows instead of returning only chat text.",
    "usecases.literature.2":
      "Read papers, generate paper notes, and carry them forward into note synthesis and hypothesis queues.",
    "usecases.literature.3":
      "Attach findings to a claim/evidence graph that traces back to papers, notes, experiments, and artifacts.",
    "usecases.writing.1":
      "Turn earlier literature and experiment output into writing tasks, draft artifacts, and review/follow-up stages.",
    "usecases.writing.2":
      "Use decision logs, writing notes, and claim states to keep writing moving across sessions.",
    "usecases.experiment.1":
      "Plan baseline, ablation, and stress runs with tracked parameters, inputs, outputs, metrics, and result bundles.",
    "usecases.experiment.2":
      "Ingest command, notebook, or external execution results and run contract validation automatically.",
    "usecases.tracking.1":
      "See execution health, recent blockers, overdue remediation, and ready-to-retry workflows from the project dashboard.",
    "usecases.tracking.2":
      "Batch dispatch remediation tasks, batch execute safe fixes, or resume workflows that are ready to move again.",
    "usecases.collaboration.1":
      "Push blockers, paper watches, writing todos, and research progress through the console and messaging channels.",
    "usecases.explore.1":
      "Build your own long-running research automation around `/api/research/*` and the `research_workflows` skill.",
    "quickstart.title": "Quick start",
    "quickstart.hintBefore": "Install → init → start. Deployment details: ",
    "quickstart.hintLink": "docs",
    "quickstart.hintAfter": ".",
    "quickstart.optionPip": "source install",
    "quickstart.badgeRecommended": "Recommended",
    "quickstart.badgeBeta": "Beta",
    "quickstart.optionLocal": "local install",
    "quickstart.tabPip": "source install (recommended)",
    "quickstart.tabPipMain": "source install",
    "quickstart.tabPipSub": "(recommended)",
    "quickstart.tabUnix": "macOS / Linux (Beta)",
    "quickstart.tabUnixMain": "macOS / Linux",
    "quickstart.tabUnixSub": "(Beta)",
    "quickstart.tabWindows": "Windows (Beta)",
    "quickstart.tabWindowsMain": "Windows",
    "quickstart.tabWindowsSub": "(Beta)",
    "quickstart.tabDocker": "Docker",
    "quickstart.tabDockerShort": "Docker",
    "quickstart.optionDocker": "Docker image",
    "quickstart.tabPipShort": "Source",
    "quickstart.tabUnixShort": "Mac/Linux",
    "quickstart.tabWindowsShort": "Windows",
    footer: "ResearchClaw — Local-first Research OS",
    "footer.builtWith": "Built with Python + FastAPI",
    "docs.backToTop": "Back to top",
    "docs.copy": "Copy",
    "docs.copied": "Copied",
    "docs.searchPlaceholder": "Search docs",
    "docs.searchLoading": "Loading…",
    "docs.searchNoResults": "No results",
    "docs.searchResultsTitle": "Search results",
    "docs.searchResultsTitleEmpty": "Search docs",
    "docs.searchHint": "Enter a keyword and press Enter to search.",
  },
};

export function t(lang: Lang, key: string): string {
  return i18n[lang][key] ?? key;
}
