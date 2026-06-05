# 文渊问史 docs 索引

本目录保存项目开发标准文件。后续开发前先阅读本索引，再按具体任务查阅对应规范。

## 文件路径

- `docs/01_requirements.md`：项目需求、阶段目标、功能范围。
- `docs/02_technical_architecture.md`：前后端分离架构、后端服务、数据库、模型兼容方案。
- `docs/03_design_guidelines.md`：前端古风视觉、交互、文本展示规范。
- `docs/04_development_steps.md`：分阶段开发步骤和每一步交付边界。
- `docs/05_quality_and_safety.md`：测试、验证、变更安全、日志记录标准。
- `docs/06_browser_acceptance.md`：浏览器人工验收清单。
- `docs/07_llm_configuration.md`：真实大模型配置与降级说明。
- `docs/08_springboot_decision.md`：是否加入 Spring Boot 的架构决策。
- `docs/09_prepared_mock_databases.md`：预置模拟数据库与检索接口说明。
- `research_code/README.md`：论文阶段检索、预处理与实验脚本归档说明。

## 工作说明

1. 每次开发只选择一个小目标，不跨阶段混做。
2. 开发前更新当日开发日志的“计划事项”。
3. 完成后更新当日开发日志的“完成事项”“验证结果”“待办事项”。
4. 若需求、架构或设计发生变化，先更新 `docs` 中对应规范，再改代码。
5. 所有新功能必须至少经过一次本地静态检查或启动验证。
