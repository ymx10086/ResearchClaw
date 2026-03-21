export interface SiteConfig {
  projectName: string;
  projectTaglineEn: string;
  projectTaglineZh: string;
  repoUrl: string;
  docsPath: string;
  showTestimonials?: boolean;
}

const defaultConfig: SiteConfig = {
  projectName: "ResearchClaw",
  projectTaglineEn: "Local-first Research OS",
  projectTaglineZh: "本地优先的 Research OS",
  repoUrl: "https://github.com/MingxinYang/ResearchClaw",
  docsPath: "/docs/",
  showTestimonials: true,
};

let cached: SiteConfig | null = null;

export async function loadSiteConfig(): Promise<SiteConfig> {
  if (cached) return cached;
  try {
    const base = import.meta.env.BASE_URL ?? "/";
    const r = await fetch(`${base}site.config.json`);
    if (r.ok) {
      cached = (await r.json()) as SiteConfig;
      return cached;
    }
  } catch {
    /* use defaults */
  }
  return defaultConfig;
}
