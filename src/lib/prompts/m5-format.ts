export const M5_FORMAT_PROMPT = `你是短剧脚本格式转换工程师。把以下半结构化剧本转换成原子 shot 格式。

===== 输出格式严格规则 =====
每一个 shot 占 3 行：
[SCENE] 场景描述（地点+时间+氛围）
[ACTION] 角色微动作（一句，可演的）
[SPEAKER] 角色名: 台词（或 OS）

一个 ACTION 对应一个 SPEAKER；如果是纯动作无台词，则 SPEAKER 行为空字符串。
SPEAKER 前必须贴微动作 ACTION 并状态呼应。
不要合并多个动作到一个 ACTION 里。

===== 输入剧本 =====
{{DRAFT}}

===== 输出 =====
直接输出转换后的脚本，不要任何额外说明或标题。`;
