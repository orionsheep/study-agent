import json

from fastapi.testclient import TestClient

from app.main import app
from app.database.store import get_store
from app.hermes_runtime.task_executor import HermesTaskResult
from app.schemas.app_protocol import LearningResource


client = TestClient(app)


def test_chat_stream_emits_agent_stream_variants():
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"student_id": "demo-student", "course_id": "ai-course", "conversation_id": "demo", "message": "生成动能定理演示"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    events = []
    for block in body.split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))
    types = {event["type"] for event in events}
    assert "run.started" in types
    assert "run.step" in types
    assert "app.create" in types
    assert "app.link.create" in types
    assert "assistant.delta" in types
    assert "dashboard.update" in types
    assert "run.done" in types
    # Unified orchestrator: Hermes generates directly, no separate model_gateway step
    assert any(event["type"] == "run.step" and event["step_name"] == "hermes_runtime" for event in events)
    assert any(event["type"] == "run.step" and event["step_name"] == "capability_contract" for event in events)
    assert any(event.get("text", "") for event in events if event["type"] == "assistant.delta")


def test_chat_stream_emits_video_cards_and_canvas_app(monkeypatch):
    async def no_live_search(*args, **kwargs):
        return []

    monkeypatch.setattr("app.agents.orchestrator_agent.search_bilibili_videos", no_live_search)
    get_store().save_resource(
        LearningResource(
            resource_id="res-video-stream-ds",
            type="video",
            title="数据结构与算法 B站视频课",
            target_topic="数据结构与算法",
            difficulty="中级",
            content={"url": "https://www.bilibili.com/video/BVSTREAM", "author": "测试UP", "description": "链表、树、排序", "play": 120000},
            source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-stream-ds", "course_id": "ai-course", "chapter": "数据结构与算法"}],
            personalized_reason="流式视频测试",
            tags=["#B站视频", "#数据结构与算法"],
        ),
        student_id="student-default",
        course_id="course-bilibili-recommendations",
        created_by_skill="test",
    )
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"student_id": "demo-student", "course_id": "ai-course", "conversation_id": "demo-video", "message": "帮我找数据结构与算法的B站视频"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    events = []
    for block in body.split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))
    resource_events = [event for event in events if event["type"] == "resource.create"]
    app_events = [event for event in events if event["type"] == "app.create"]
    assistant_text = "".join(event.get("text", "") for event in events if event["type"] == "assistant.delta")
    first_assistant_index = next(i for i, event in enumerate(events) if event["type"] == "assistant.delta")
    first_artifact_index = min(i for i, event in enumerate(events) if event["type"] in {"resource.create", "app.create"})
    assert any(event["resource"]["type"] == "video" for event in resource_events)
    assert any(event.get("message_id") for event in resource_events)
    assert first_assistant_index < first_artifact_index
    assert "https://www.bilibili.com/video/BVSTREAM" in assistant_text
    assert "数据结构与算法 B站视频课" in assistant_text
    video_apps = [event["app"] for event in app_events if event["app"]["app_type"] == "video.player"]
    assert video_apps
    assert video_apps[0]["payload"]["videos"]
    assert any(
        "BVSTREAM" in str(video.get("content", {}).get("url", ""))
        for video in video_apps[0]["payload"]["videos"]
    )
    assert video_apps[0]["payload"]["selected_bvid"].startswith("BV")
    assert "player.bilibili.com/player.html" in video_apps[0]["payload"]["embed_url"]
    assert not any(event["app"]["app_type"] == "resource.center" and event["app"]["payload"].get("resource_kind") == "video" for event in app_events)
    assert any(event["type"] == "run.step" and event["step_name"] == "bilibili_live_search" for event in events)


def test_chat_stream_emits_ppt_generation_progress_steps(monkeypatch):
    async def mock_ppt_hermes(self, plan, context, rag_context, **kwargs):
        return HermesTaskResult(
            capability="ppt",
            topic="大学物理",
            summary="大学物理 PPT 已生成。",
            apps=[
                {
                    "app_type": "custom.html",
                    "title": "大学物理简单介绍 PPT",
                    "payload": {
                        "html": (
                            "<!DOCTYPE html><html><body><main class='deck' data-deck='physics'>"
                            "<section class='slide' data-slide='1'><h1>大学物理简单介绍</h1><p>本页介绍力学、电磁学和热学的课程结构。</p></section>"
                            "<section class='slide' data-slide='2'><h2>学习主线</h2><p>围绕模型、公式、实验和误差分析，建立定量推理能力。</p></section>"
                            "<script>document.addEventListener('keydown',(event)=>{if(event.key==='ArrowRight'){};});</script>"
                            "</main></body></html>"
                        )
                    },
                }
            ],
            trace=["mock_ppt_generated"],
        )

    monkeypatch.setattr("app.hermes_runtime.task_executor.HermesTaskExecutor.run_hermes", mock_ppt_hermes)
    monkeypatch.setattr("app.agents.orchestrator_agent.HermesTaskExecutor.run_hermes", mock_ppt_hermes)

    with client.stream(
        "POST",
        "/api/chat/stream",
            json={"student_id": "demo-student", "course_id": "ai-course", "conversation_id": "demo-ppt-stream-mock", "message": "生成一套大学物理的简单介绍ppt"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    events = []
    for block in body.split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))

    step_names = [event["step_name"] for event in events if event["type"] == "run.step"]
    # Unified orchestrator: Hermes handles PPT generation internally (skill_call events)
    assert "hermes_runtime" in step_names
    assert "canvas_materializer" in step_names
    assert any(event["type"] == "app.create" and event["app"]["app_type"] == "custom.html" for event in events)
    assert any(event["type"] == "resource.create" and event["resource"]["type"] == "ppt" for event in events)
    assert not any(event["type"] == "consent_required" for event in events)
