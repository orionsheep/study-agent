from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.database.store import get_store
from app.rag.knowledge_graph import KnowledgeGraphBuilder
from app.rag.retriever import CourseRetriever
from app.safety.verifier import ResourceVerifier
from app.schemas.app_protocol import LearningResource
from app.video.search import search_bilibili_videos


client = TestClient(app)


def test_rag_retrieval_has_source_refs_and_graph_edges():
    chunks = CourseRetriever().retrieve("梯度下降")
    assert chunks
    assert all(chunk["source_ref"] for chunk in chunks)
    graph = KnowledgeGraphBuilder().graph("ai-course")
    assert graph["nodes"]
    assert graph["edges"]


def test_rag_retrieval_does_not_fallback_to_unrelated_chunks():
    context = CourseRetriever().context_with_refs("今天我只想要一个安静的番茄钟提醒", course_id="ai-course")
    assert context["has_relevant_context"] is False
    assert context["context"] == ""
    assert context["source_refs"] == []


def test_video_search_uses_global_bilibili_resource_pool():
    store = get_store()
    resource = LearningResource(
        resource_id="res-video-test-ds",
        type="video",
        title="数据结构与算法 B站精讲",
        target_topic="数据结构与算法",
        difficulty="中级",
        content={
            "url": "https://www.bilibili.com/video/BVTEST",
            "bvid": "BVTEST",
            "author": "测试UP",
            "description": "覆盖链表、栈、队列、树和排序。",
            "play": 280000,
            "tags": ["#数据结构与算法", "#B站视频"],
        },
        source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-test-ds", "course_id": "course-bilibili-recommendations", "chapter": "数据结构与算法"}],
        personalized_reason="测试跨课程视频池",
        tags=["#数据结构与算法", "#B站视频"],
    )
    store.save_resource(resource, student_id="student-default", course_id="course-bilibili-recommendations", created_by_skill="test")
    videos = store.search_video_resources("数据结构视频", limit=3)
    assert videos
    assert any(video.resource_id == "res-video-test-ds" for video in videos)


def test_video_search_keeps_c_language_course_query_relevant():
    store = get_store()
    resource_ids = (
        "res-video-test-c-star-primary",
        "res-video-test-c-star-web",
        "res-video-test-c-star-go",
        "res-video-test-c-star-setup",
    )
    store.execute(f"DELETE FROM resources WHERE id IN ({','.join('?' for _ in resource_ids)})", resource_ids)
    try:
        fixtures = [
            LearningResource(
                resource_id="res-video-test-c-star-primary",
                type="video",
                title="C语言零基础星轨课程",
                target_topic="C语言",
                difficulty="入门",
                content={
                    "url": "https://www.bilibili.com/video/BVSTAR01",
                    "bvid": "BVSTAR01",
                    "author": "测试C语言UP",
                    "description": "C语言程序设计、指针、数组和函数入门。",
                    "play": 220000,
                    "tags": ["#C语言", "#星轨课程"],
                },
                source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-c-star", "course_id": "course-bilibili-recommendations"}],
                personalized_reason="测试 C 语言强相关",
                tags=["#C语言", "#星轨课程"],
            ),
            LearningResource(
                resource_id="res-video-test-c-star-web",
                type="video",
                title="星轨Web前端实战课程",
                target_topic="Web前端",
                difficulty="入门",
                content={"url": "https://www.bilibili.com/video/BVSTAR02", "bvid": "BVSTAR02", "author": "测试WebUP", "description": "HTML、CSS、JavaScript。", "play": 999999},
                source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-web-star", "course_id": "course-bilibili-recommendations"}],
                personalized_reason="测试无关 Web",
                tags=["#Web前端"],
            ),
            LearningResource(
                resource_id="res-video-test-c-star-go",
                type="video",
                title="8小时星轨Go语言课程",
                target_topic="Go语言",
                difficulty="入门",
                content={"url": "https://www.bilibili.com/video/BVSTAR03", "bvid": "BVSTAR03", "author": "测试GoUP", "description": "简介里会对比 C语言，但标题和主题是 Go。", "play": 999999},
                source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-go-star", "course_id": "course-bilibili-recommendations"}],
                personalized_reason="测试简介误命中",
                tags=["#Go语言"],
            ),
            LearningResource(
                resource_id="res-video-test-c-star-setup",
                type="video",
                title="Dev C++星轨安装和C语言教程",
                target_topic="C/C++开发环境",
                difficulty="入门",
                content={"url": "https://www.bilibili.com/video/BVSTAR04", "bvid": "BVSTAR04", "author": "测试环境UP", "description": "安装配置开发环境。", "play": 999999},
                source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-setup-star", "course_id": "course-bilibili-recommendations"}],
                personalized_reason="测试安装配置误命中",
                tags=["#C语言", "#开发环境"],
            ),
        ]
        for resource in fixtures:
            store.save_resource(resource, student_id="student-default", course_id="course-bilibili-recommendations", created_by_skill="test")

        videos = store.search_video_resources("请你给我推荐一些C语言星轨视频课程", limit=6)
        result_ids = [video.resource_id for video in videos]
        assert result_ids[:1] == ["res-video-test-c-star-primary"]
        assert "res-video-test-c-star-web" not in result_ids
        assert "res-video-test-c-star-go" not in result_ids
        assert "res-video-test-c-star-setup" not in result_ids
    finally:
        store.execute(f"DELETE FROM resources WHERE id IN ({','.join('?' for _ in resource_ids)})", resource_ids)


def test_video_search_keeps_rubik_query_topic_bound():
    store = get_store()
    resource_ids = (
        "res-video-test-rubik-good",
        "res-video-test-rubik-bad",
    )
    store.execute(f"DELETE FROM resources WHERE id IN ({','.join('?' for _ in resource_ids)})", resource_ids)
    try:
        fixtures = [
            LearningResource(
                resource_id="res-video-test-rubik-good",
                type="video",
                title="三阶魔方还原入门教程",
                target_topic="魔方还原",
                difficulty="入门",
                content={
                    "url": "https://www.bilibili.com/video/BVRUBIK01",
                    "bvid": "BVRUBIK01",
                    "author": "测试魔方UP",
                    "description": "讲解底层十字、层先法和手法记号。",
                    "play": 120000,
                    "tags": ["#魔方", "#三阶魔方", "#层先法"],
                },
                source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-rubik-good", "course_id": "course-bilibili-recommendations"}],
                personalized_reason="测试魔方强相关",
                tags=["#魔方"],
            ),
            LearningResource(
                resource_id="res-video-test-rubik-bad",
                type="video",
                title="成年人必备资源网站，个个都是宝藏",
                target_topic="娱乐网站",
                difficulty="adaptive",
                content={
                    "url": "https://www.bilibili.com/video/BVRUBIK02",
                    "bvid": "BVRUBIK02",
                    "author": "测试无关UP",
                    "description": "泛娱乐资源推荐。",
                    "play": 999999,
                    "tags": ["#资源网站"],
                },
                source_refs=[{"document_id": "doc-bilibili-videos", "chunk_id": "chunk-rubik-bad", "course_id": "course-bilibili-recommendations"}],
                personalized_reason="测试无关泛娱乐",
                tags=["#资源网站"],
            ),
        ]
        for resource in fixtures:
            store.save_resource(resource, student_id="student-default", course_id="course-bilibili-recommendations", created_by_skill="test")

        videos = store.search_video_resources("给我推荐一些魔方还原教学视频", limit=6)
        result_ids = [video.resource_id for video in videos]
        assert "res-video-test-rubik-good" in result_ids
        assert "res-video-test-rubik-bad" not in result_ids
    finally:
        store.execute(f"DELETE FROM resources WHERE id IN ({','.join('?' for _ in resource_ids)})", resource_ids)


@pytest.mark.asyncio
async def test_live_bilibili_search_does_not_fallback_to_irrelevant_raw_results(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": 0,
                "data": {
                    "result": [
                        {
                            "bvid": "BVJUNK01",
                            "title": "成年人必备资源网站，个个都是宝藏",
                            "description": "泛娱乐资源推荐",
                            "tag": "资源网站",
                            "author": "无关UP",
                            "play": 999999,
                        }
                    ]
                },
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.video.search.httpx.AsyncClient", FakeAsyncClient)
    videos = await search_bilibili_videos("魔方还原教程", limit=6)
    assert videos == []


def test_verifier_fails_missing_source_refs_and_unsafe_code():
    resource = LearningResource(type="document", title="No refs", target_topic="x", content={}, source_refs=[], personalized_reason="x")
    result = ResourceVerifier().verify(resource)
    assert result.passed is False
    code = LearningResource(
        type="code_practice",
        title="Unsafe",
        target_topic="x",
        content={"starter_code": "eval('1')"},
        source_refs=[{"document_id": "d", "chunk_id": "c", "course_id": "ai-course", "confidence": 0.9}],
        personalized_reason="x",
    )
    assert ResourceVerifier().verify(code).passed is False


def test_valid_rag_grounded_resource_passes():
    refs = [chunk["source_ref"] for chunk in CourseRetriever().retrieve("梯度下降")]
    resource = LearningResource(type="document", title="Grounded", target_topic="梯度下降", content={"summary": "ok"}, source_refs=refs, personalized_reason="fits profile")
    result = ResourceVerifier().verify(resource)
    assert result.passed is True
    assert result.source_coverage > 0.8


def test_course_document_upload_persists_chunks_and_refs(monkeypatch):
    monkeypatch.setattr("app.database.store.embed_text", lambda text, task_type="RETRIEVAL_DOCUMENT": [0.12] * 16)
    course_id = "test-course-upload"
    title = "NotebookLM 风格测试资料"
    content = """# NotebookLM 风格测试资料

这份资料专门用于验证上传后会进入 RAG chunk，而不是只检索旧资料。

## 引用能力

上传资料需要生成 source_ref、snippet 和 score，后续回答可以引用这些来源。
"""
    response = client.post(
        f"/api/courses/{course_id}/documents",
        json={"title": title, "content": content},
        headers={"X-Student-Id": "test-student", "X-Course-Id": course_id, "X-Conversation-Id": "test-conversation"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["chunk_count"] >= 1
    assert payload["source_refs"][0]["document_id"] == payload["document_id"]
    assert payload["retrieved_chunks"]
    assert payload["retrieved_chunks"][0]["source_ref"]["document_id"] == payload["document_id"]
    assert "score" in payload["retrieved_chunks"][0]
    assert "snippet" in payload["retrieved_chunks"][0]
