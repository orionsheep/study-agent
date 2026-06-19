# english-word-fission 数据目录

本目录的**词库静态数据**不进 git（体积大、文件数极多），但运行时必需。
克隆仓库后，需要从原始项目或备份补齐以下文件/目录：

| 路径 | 体积 | 说明 |
|------|------|------|
| `word_chinese/` | ~103MB（数万个 `*.json`） | 单词 → 中文释义逐词 JSON |
| `word_text_database/` | ~92MB（`word_database/` 内 2.3 万文件） | 单词文本数据库 |
| `ecdict_extracted.csv` | ~42MB | ECDICT 词典抽取 |
| `word_fission_data.csv` | ~6MB | 单词拆分（fission）数据 |
| `word_library/` | ~1.5MB | 推荐/考纲词库（四六级、托福等） |

> `ai_prompts/`（prompt 模板）**会**进 git，无需补齐。

## 缺少这些数据时

服务仍能启动，但单词查询会返回空。启动脚本 `scripts/dev.sh` 不会校验数据完整性。
