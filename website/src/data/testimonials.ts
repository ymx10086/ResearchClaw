/**
 * Testimonials (community voices) data.
 * REAL_TESTIMONIALS: production-only; section is hidden when empty in build.
 * MOCK_TESTIMONIALS: dev-only; shown together with real in dev mode.
 */
export interface TestimonialItem {
  avatar: string;
  quoteEn: string;
  quoteZh: string;
  username: string;
  url: string;
}

/** Real community testimonials. Section hidden in build when this is empty. */
export const REAL_TESTIMONIALS: TestimonialItem[] = [];

/** Mock data for dev: shown only in dev together with REAL_TESTIMONIALS. */
export const MOCK_TESTIMONIALS: TestimonialItem[] = [
  {
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=alex",
    quoteEn:
      "ResearchClaw tracks new ArXiv papers in my field every day and pushes " +
      "summaries to Feishu. Saves me hours of manual browsing.",
    quoteZh:
      "ResearchClaw 每天自动追踪我关注领域的 ArXiv 新论文，推摘要到飞书，省了大量手动浏览时间。",
    username: "@researcher_a",
    url: "#",
  },
  {
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=brooke",
    quoteEn:
      "The BibTeX management and citation formatting are game-changers. " +
      "No more wrestling with reference lists.",
    quoteZh: "BibTeX 管理和引用格式化太好用了，再也不用手动折腾参考文献列表。",
    username: "@phd_student_b",
    url: "#",
  },
  {
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=casey",
    quoteEn:
      "Set up in 5 minutes with pip install. The Skills system lets me " +
      "customize workflows for my lab's needs.",
    quoteZh:
      "pip install 五分钟搞定，Skills 系统让我按实验室需求定制自动化工作流。",
    username: "@lab_lead_c",
    url: "#",
  },
  {
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=drew",
    quoteEn:
      "Multi-channel support is brilliant. I get paper alerts on Discord " +
      "and deadline reminders on DingTalk.",
    quoteZh:
      "多频道支持太赞了，Discord 收论文提醒，钉钉收 DDL 通知，各司其职。",
    username: "@postdoc_d",
    url: "#",
  },
  {
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=emery",
    quoteEn:
      "Data stays local, which is crucial for our unpublished research. " +
      "Cloud deployment is optional — exactly right.",
    quoteZh: "数据本地存储，对我们未发表的研究很关键。云部署可选，正合需求。",
    username: "@pi_emery",
    url: "#",
  },
];
