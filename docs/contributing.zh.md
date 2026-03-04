# 贡献指南

感谢你对 ResearchClaw 的贡献兴趣！

## 开发环境

### 后端（Python）

```bash
# 克隆仓库
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装开发依赖
pip install -e ".[dev]"
```

### 控制台（前端）

```bash
cd console
npm install
npm run dev
```

### 官网（前端）

```bash
cd website
npm install
npm run dev
```

## 贡献流程

1. Fork 仓库
2. 创建特性分支：`git checkout -b feature/my-feature`
3. 提交修改：`git commit -m "feat: add my feature"`
4. 推送分支：`git push origin feature/my-feature`
5. 创建 Pull Request

## 代码规范

- Python 代码遵循 PEP 8
- TypeScript 代码使用 ESLint + Prettier
- Commit 信息遵循 Conventional Commits 规范

## Skill 贡献

开发自定义 Skill：

1. 参考 [Skills 文档](./skills.md) 了解 Skill 结构
2. 在 `skills/` 目录下创建新 Skill
3. 编写 `skill.json` 和处理逻辑
4. 测试确保功能正常
5. 提交 PR 或发布到独立仓库

## 问题反馈

- 使用 GitHub Issues 报告 Bug
- 提供复现步骤和环境信息
- 附上相关的日志输出
