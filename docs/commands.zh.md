# 命令系统

ResearchClaw 支持在对话中使用命令来控制系统行为。

## 可用命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/compact` | 手动触发对话压缩 |
| `/clear` | 清除当前会话的对话历史 |
| `/reset` | 重置助手状态 |
| `/skills` | 列出已安装的 Skills |
| `/install <url>` | 从 GitHub 安装 Skill |
| `/uninstall <name>` | 卸载 Skill |

## 使用方式

在任意频道的对话中，以 `/` 开头输入命令：

```
/help
```

```
/install https://github.com/user/my-skill
```

## 命令与自然语言

除了命令，你也可以用自然语言描述需求，AI 助手会理解并执行对应操作：

```
帮我安装这个 Skill: https://github.com/user/my-skill
```

效果等同于 `/install https://github.com/user/my-skill`。
