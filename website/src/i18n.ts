export type Lang = "zh" | "en";

export const i18n: Record<Lang, Record<string, string>> = {
  zh: {
    "nav.docs": "文档",
    "nav.github": "GitHub",
    "nav.lang": "EN",
    "hero.slogan": "你的 AI 科研助手",
    "hero.sub":
      "论文搜索与追踪、文献管理、实验记录、数据分析——一站式科研辅助工具，支持多端接入。",
    "hero.cta": "查看文档",
    "brandstory.title": "Why ResearchClaw？",
    "brandstory.para1":
      "ResearchClaw 取自 Research（科研）和 Claw（利爪），寓意为你的科研之路披荆斩棘、深入挖掘。",
    "brandstory.para2":
      "我们希望它成为你最得力的科研伙伴，帮你追踪最新论文、管理文献、分析数据，让你专注于真正的创新。",
    "features.title": "核心能力",
    "features.papers.title": "论文搜索与追踪",
    "features.papers.desc":
      "支持 ArXiv、Semantic Scholar 等论文源，自动追踪研究领域最新成果并推送摘要。",
    "features.references.title": "文献管理",
    "features.references.desc":
      "BibTeX 管理、引用格式化、文献库检索，科研写作的得力助手。",
    "features.analysis.title": "实验与分析",
    "features.analysis.desc":
      "实验记录、数据分析、可视化——从实验设计到结果呈现全流程支持。",
    "features.channels.title": "全域触达",
    "features.channels.desc":
      "支持钉钉、飞书、QQ、Discord、iMessage 等频道，随时随地获取科研动态。",
    "features.skills.title": "Skills 扩展",
    "features.skills.desc":
      "内置科研技能，自定义扩展，定时任务（论文日报、DDL 提醒等）。",
    "features.private.title": "本地掌控",
    "features.private.desc":
      "数据本地存储，研究笔记与实验记录由你掌控，支持云端部署。",
    "testimonials.title": "社区怎么说",
    "testimonials.viewAll": "查看全部",
    "usecases.title": "你可以用 ResearchClaw 做什么",
    "usecases.sub": "",
    "usecases.category.literature": "文献与论文",
    "usecases.category.writing": "学术写作",
    "usecases.category.experiment": "实验管理",
    "usecases.category.tracking": "科研追踪",
    "usecases.category.collaboration": "协作与共享",
    "usecases.category.explore": "探索更多",
    "usecases.literature.1":
      "每日自动追踪 ArXiv、Semantic Scholar 上你关注领域的新论文，生成摘要并推送到飞书、钉钉等频道。",
    "usecases.literature.2":
      "批量搜索论文、下载 PDF、自动提取元数据并加入 BibTeX 文献库。",
    "usecases.literature.3": "对已有文献进行批量分析，发现引用关系和研究趋势。",
    "usecases.writing.1":
      "自动格式化引用、生成参考文献列表，支持多种引用格式。",
    "usecases.writing.2":
      "阅读论文并生成结构化摘要，提取方法论、关键发现和局限性。",
    "usecases.experiment.1":
      "记录实验参数与结果，支持自然语言查询历史实验数据。",
    "usecases.experiment.2": "定期提醒论文投稿 DDL、项目里程碑和待办事项。",
    "usecases.tracking.1":
      "追踪特定作者、会议、期刊的最新发表，及时获取领域动态。",
    "usecases.tracking.2": "自动监控竞品或相关研究的进展，生成竞争分析报告。",
    "usecases.collaboration.1":
      "通过频道将论文摘要、实验进展分享给团队成员，促进协作。",
    "usecases.explore.1": "用 Skills 与定时任务打造你专属的科研自动化工作流。",
    "quickstart.title": "快速开始",
    "quickstart.hintBefore": "安装 → 初始化 → 启动；频道配置见 ",
    "quickstart.hintLink": "文档",
    "quickstart.hintAfter": "，即可开始使用 ResearchClaw。",
    "quickstart.optionPip": "pip 安装",
    "quickstart.badgeRecommended": "推荐",
    "quickstart.badgeBeta": "Beta",
    "quickstart.optionLocal": "一键安装（uv 建虚拟环境并安装，无需 Python）",
    "quickstart.tabPip": "pip 安装 (推荐)",
    "quickstart.tabPipMain": "pip 安装",
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
    "quickstart.tabPipShort": "pip",
    "quickstart.tabUnixShort": "Mac/Linux",
    "quickstart.tabWindowsShort": "Windows",
    footer: "ResearchClaw — 你的 AI 科研助手",
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
    "hero.slogan": "Your AI Research Assistant",
    "hero.sub":
      "Paper search & tracking, reference management, experiment logging, data analysis — an all-in-one research assistant with multi-channel support.",
    "hero.cta": "Read the docs",
    "brandstory.title": "Why ResearchClaw?",
    "brandstory.para1":
      "ResearchClaw combines Research and Claw — a sharp tool that digs deep into academic knowledge on your behalf.",
    "brandstory.para2":
      "More than a cold tool, ResearchClaw is your dedicated research companion — tracking papers, managing references, analyzing data — so you can focus on innovation.",
    "features.title": "Key capabilities",
    "features.papers.title": "Paper search & tracking",
    "features.papers.desc":
      "Search ArXiv, Semantic Scholar, and more. Auto-track new publications in your fields and push daily digests.",
    "features.references.title": "Reference management",
    "features.references.desc":
      "BibTeX management, citation formatting, literature search — your academic writing companion.",
    "features.analysis.title": "Experiments & analysis",
    "features.analysis.desc":
      "Experiment logging, data analysis, visualization — full pipeline from design to presentation.",
    "features.channels.title": "Every channel",
    "features.channels.desc":
      "DingTalk, Feishu, QQ, Discord, iMessage — get research updates wherever you are.",
    "features.skills.title": "Skills",
    "features.skills.desc":
      "Built-in research skills, customizable extensions, cron (paper digest, deadline reminders).",
    "features.private.title": "Under your control",
    "features.private.desc":
      "Data stored locally, research notes under your control. Cloud deployment supported.",
    "testimonials.title": "What people say",
    "testimonials.viewAll": "View all",
    "usecases.title": "What you can do with ResearchClaw",
    "usecases.sub": "",
    "usecases.category.literature": "Literature & papers",
    "usecases.category.writing": "Academic writing",
    "usecases.category.experiment": "Experiment management",
    "usecases.category.tracking": "Research tracking",
    "usecases.category.collaboration": "Collaboration",
    "usecases.category.explore": "Explore more",
    "usecases.literature.1":
      "Daily auto-tracking of new papers from ArXiv and Semantic Scholar in your fields, with summaries pushed to Feishu, DingTalk, etc.",
    "usecases.literature.2":
      "Batch paper search, PDF download, automatic metadata extraction and BibTeX integration.",
    "usecases.literature.3":
      "Batch analysis of existing literature to discover citation relationships and research trends.",
    "usecases.writing.1":
      "Auto-format citations and generate reference lists in multiple citation styles.",
    "usecases.writing.2":
      "Read papers and generate structured summaries extracting methodology, key findings, and limitations.",
    "usecases.experiment.1":
      "Log experiment parameters and results; query historical data with natural language.",
    "usecases.experiment.2":
      "Periodic reminders for paper submission deadlines, project milestones, and tasks.",
    "usecases.tracking.1":
      "Track new publications by specific authors, conferences, or journals.",
    "usecases.tracking.2":
      "Auto-monitor related or competing research, generating competitive analysis reports.",
    "usecases.collaboration.1":
      "Share paper summaries and experiment updates with team members through channels.",
    "usecases.explore.1":
      "Combine Skills and cron into your own automated research workflows.",
    "quickstart.title": "Quick start",
    "quickstart.hintBefore": "Install → init → start. See ",
    "quickstart.hintLink": "docs",
    "quickstart.hintAfter": " for channel configuration.",
    "quickstart.optionPip": "pip install",
    "quickstart.badgeRecommended": "Recommended",
    "quickstart.badgeBeta": "Beta",
    "quickstart.optionLocal":
      "One-click: uv creates venv & installs, no Python needed",
    "quickstart.tabPip": "pip install (recommended)",
    "quickstart.tabPipMain": "pip install",
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
    "quickstart.tabPipShort": "pip",
    "quickstart.tabUnixShort": "Mac/Linux",
    "quickstart.tabWindowsShort": "Windows",
    footer: "ResearchClaw — Your AI Research Assistant",
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
