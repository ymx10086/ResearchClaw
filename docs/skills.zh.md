# Skills

Skills 是 ResearchClaw 的可扩展技能系统，为 AI 助手提供专业的科研能力。

## 内置 Skills

ResearchClaw 内置了多种科研相关技能：

- **论文搜索**：在 ArXiv、Semantic Scholar 等平台搜索论文
- **论文追踪**：定期追踪指定领域或关键词的最新论文
- **文献管理**：管理 BibTeX 文件、生成引用
- **天气查询**：查询天气信息（日常辅助）

## Skill 结构

每个 Skill 是一个独立的 Python 模块，包含：

```
my_skill/
├── __init__.py
├── skill.json          # 技能元信息
├── handler.py          # 主逻辑
└── requirements.txt    # 依赖（可选）
```

### skill.json

```json
{
  "name": "my_skill",
  "version": "1.0.0",
  "description": "A custom research skill",
  "author": "Your Name",
  "tags": ["research", "papers"]
}
```

## 安装 Skill

### 从 GitHub 安装

在对话中发送：

```
安装 skill https://github.com/user/repo
```

### 手动安装

将 Skill 文件夹放入工作目录的 `skills/` 文件夹中。

## 定时任务

Skills 支持 Cron 定时任务：

```python
# 在 skill.json 中配置
{
  "cron": "0 9 * * *",  # 每天早上 9 点执行
  "cron_prompt": "搜索昨天发布的 LLM Agent 相关论文"
}
```

## 自定义开发

参考 [CONTRIBUTING](./contributing.md) 了解如何开发自定义 Skill。
