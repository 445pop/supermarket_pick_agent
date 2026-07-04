# Supermarket Pick Agent

面向“小场景、有限物体类别、半结构化货架环境”的超市取货 Agent 项目。
- 上层用 ReAct Agent 做任务理解、工具调用、状态推进和失败恢复。
- 商品信息来自受控商品数据库。
- 导航模块负责移动到货架接近点和交付点。
- 到达货架后，按商品目录调用对应远端 VLA 模型服务生成动作 chunk。
- 矿泉水和方便面不是同一个 VLA endpoint 临时换 prompt，而是绑定不同 VLA 技能和远端接口。
- OpenAI/VLM verifier 只做语义验收，安全控制由执行器和机器人控制层负责。

## 演示视频

![Demo](demo.gif)

> 完整视频见仓库根目录的 `pick_cup.mp4`，clone 后本地播放。

## 目录

```text
supermarket_pick_agent/
  README.md
  requirements.txt
  .env.example
  data/products.json
  src/supermarket_pick_agent/
    main.py
    agent.py
    config.py
    database.py
    models.py
    tools.py
    interfaces/
      navigation.py
      vla_pi05.py
      openai_verifier.py
    robot/
      executor.py
```

## 快速运行

默认使用 mock 导航、mock VLA、mock VLM。

```bash
cd C:\Users\LENOVO\Desktop\supermarket_pick_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.supermarket_pick_agent.main
python -m src.supermarket_pick_agent.main mineral_water
python -m src.supermarket_pick_agent.main instant_noodle
```

输出是完整任务结果 JSON，包含 product、status、reason 和每一步 Observation history。

说明：
- 不带参数时，默认执行“帮我拿一瓶矿泉水”。
- `mineral_water` 会路由到 `water_bottle_grasp_pi05` 和水瓶抓取 endpoint。
- `instant_noodle` 会路由到 `instant_noodle_grasp_pi05` 和方便面抓取 endpoint。
- 如果 Windows 终端传中文参数出现乱码，可以先用商品 id 或英文别名演示；真实系统里用户文本应由上层 API 以 UTF-8 请求体传入。

## 核心流程

```text
用户文本任务
  -> query_product_db(keyword)
  -> navigate_to(approach_point)
  -> capture_observation()
  -> call_product_vla_grasp(product_id, endpoint from product DB)
  -> SafetyExecutor 执行动作 chunk 并返回完成状态
  -> verify_grasp_with_vlm + gripper/executor observation
  -> observation_fusion
  -> 成功后 navigate_to(delivery_point)
  -> call_product_vla_place(product_id, endpoint from product DB)
  -> verify_place_with_vlm
  -> final result
```

## 商品到 VLA 的路由

商品目录在 `data/products.json`。每个商品都保存自己的 VLA 技能名、远端 endpoint 和固定 prompt。

```json
{
  "product_id": "mineral_water",
  "vla_skill": "water_bottle_grasp_pi05",
  "vla_endpoint": "https://vla.example.com/water-bottle-grasp",
  "grasp_prompt": "grasp the water bottle by the middle body"
}
```

当前示例：

- `mineral_water` -> `water_bottle_grasp_pi05` -> `https://vla.example.com/water-bottle-grasp`
- `instant_noodle` -> `instant_noodle_grasp_pi05` -> `https://vla.example.com/instant-noodle-grasp`
- 放置动作统一走 `delivery_area_place_pi05` 示例 endpoint

真实接入时，把 `vla_endpoint` 和 `place_vla_endpoint` 换成你的 pi0.5/VLA 服务地址即可。

## 如何接真实模块

1. 导航模块：实现或替换 `interfaces/navigation.py` 的 `HttpNavigationClient.navigate_to()`。
2. VLA 模型服务：实现或替换 `interfaces/vla_pi05.py`。真实请求会把 `product_id`、`vla_skill`、`fixed_prompt`、图像路径、机器人状态、夹爪状态和失败上下文发给商品绑定的 endpoint。
3. OpenAI/VLM 验收：配置 `.env` 里的 `OPENAI_API_KEY` 和 `OPENAI_VERIFIER_MODEL`，或替换 `interfaces/openai_verifier.py`。
4. 机器人执行：替换 `robot/executor.py` 中的 mock 执行逻辑，接入 Aubo 和 RG75 控制接口。
5. Observation 融合：当前在 `agent.py` 内融合 VLM、夹爪和 executor 状态。真实项目可以抽成独立 verifier/fusion 模块。

## 重要边界

- ReAct Agent 不直接输出关节角或底层控制命令。
- Agent 负责选择商品、导航点、VLA endpoint 和失败恢复策略。
- VLA/pi0.5 负责到点后的动作 chunk 生成。
- 一个 VLA 模型服务对应一个固定 prompt/技能；Agent 不在运行时自由改写 VLA prompt。
- VLM 只做语义验收，不做安全控制。
- 动作是否执行完毕由执行器和机器人 I/O 判断，例如 `all_steps_sent`、`controller_done`、`settled`。
- 抓取是否成功由 VLM、夹爪宽度/力反馈和执行器状态融合判断。

## 失败恢复策略

当前代码支持以下恢复思路：

- 商品查不到、库存为 0 或命中多个候选：不继续导航，直接失败或等待上层确认。
- 导航失败：不进入抓取阶段。
- 动作被安全层拒绝：立即停止，不盲目重试。
- 空抓或 VLM 判断失败：重新观察，并再次调用该商品绑定的 VLA endpoint。
- 多次失败：超过 `max_retry` 后停止，保留失败 Observation。

## 环境变量

```env
OPENAI_API_KEY=
OPENAI_VERIFIER_MODEL=gpt-5.5
PI05_ENDPOINT=http://127.0.0.1:8088/v1/action
NAVIGATION_ENDPOINT=http://127.0.0.1:8090/v1/navigate
USE_MOCKS=true
```

说明：

- `USE_MOCKS=true` 时，不调用真实导航、VLA 和 OpenAI。
- `USE_MOCKS=false` 时，会调用 `HttpNavigationClient`、商品目录中的 VLA endpoint，以及 OpenAI/VLM verifier。
- 如果真实平台没有 `gpt-5.5` 这个模型名，请把 `OPENAI_VERIFIER_MODEL` 改成实际可用模型。
