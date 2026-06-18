from uuid import uuid4

from app.database.store import get_store


def test_list_chat_messages_restores_saved_app_links():
    store = get_store()
    suffix = uuid4().hex
    student_id = f"student-link-restore-{suffix}"
    course_id = f"course-link-restore-{suffix}"
    conversation_id = f"conversation-link-restore-{suffix}"
    message_id = f"chatmsg-link-restore-{suffix}"
    app_id = f"app-link-restore-{suffix}"
    run_id = f"run-link-restore-{suffix}"
    message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="已生成一份 PPT。",
        message_id=message_id,
    )
    link = store.create_chat_link(
        message["id"],
        app_id,
        "打开 历史总结 PPT",
        action="fullscreen",
        run_id=run_id,
    )

    messages = store.list_chat_messages(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        limit=10,
    )

    assert messages == [
        {
            **message,
            "links": [
                {
                    "link_id": link.link_id,
                    "message_id": message["id"],
                    "app_id": app_id,
                    "label": "打开 历史总结 PPT",
                    "action": "fullscreen",
                    "anchor_text": "打开 历史总结 PPT",
                    "created_at": link.created_at,
                    "source_run_id": run_id,
                }
            ],
            "resources": [],
        }
    ]


def test_list_chat_messages_restores_stream_links_by_run_id():
    store = get_store()
    suffix = uuid4().hex
    student_id = f"student-run-link-restore-{suffix}"
    course_id = f"course-run-link-restore-{suffix}"
    conversation_id = f"conversation-run-link-restore-{suffix}"
    run_id = f"run-stream-link-restore-{suffix}"
    history_message_id = f"chatmsg-run-link-restore-{suffix}"
    stream_message_id = f"msg-run-link-restore-{suffix}"
    app_id = f"app-run-link-restore-{suffix}"
    message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="PPT 已推送到画布。",
        metadata={"run_id": run_id},
        message_id=history_message_id,
    )
    link = store.create_chat_link(
        stream_message_id,
        app_id,
        "打开 总结 PPT",
        action="fullscreen",
        run_id=run_id,
    )

    messages = store.list_chat_messages(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        limit=10,
    )

    assert messages[0]["id"] == message["id"]
    assert messages[0]["links"] == [
        {
            "link_id": link.link_id,
            "message_id": history_message_id,
            "app_id": app_id,
            "label": "打开 总结 PPT",
            "action": "fullscreen",
            "anchor_text": "打开 总结 PPT",
            "created_at": link.created_at,
            "source_run_id": run_id,
        }
    ]
    assert messages[0]["resources"] == []


def test_list_chat_messages_attaches_run_links_to_latest_assistant_message_only():
    store = get_store()
    suffix = uuid4().hex
    student_id = f"student-latest-link-restore-{suffix}"
    course_id = f"course-latest-link-restore-{suffix}"
    conversation_id = f"conversation-latest-link-restore-{suffix}"
    run_id = f"run-latest-link-restore-{suffix}"
    app_id = f"app-latest-link-restore-{suffix}"
    first_message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="正在生成 PPT。",
        metadata={"run_id": run_id},
        message_id=f"chatmsg-latest-link-first-{suffix}",
    )
    latest_message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="PPT 已完成。",
        metadata={"run_id": run_id},
        message_id=f"chatmsg-latest-link-final-{suffix}",
    )
    store.create_chat_link(
        f"msg-latest-link-stream-{suffix}",
        app_id,
        "打开 完成 PPT",
        action="fullscreen",
        run_id=run_id,
    )

    messages = store.list_chat_messages(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        limit=10,
    )

    by_id = {message["id"]: message for message in messages}
    assert by_id[first_message["id"]]["links"] == []
    assert by_id[first_message["id"]]["resources"] == []
    assert by_id[latest_message["id"]]["links"][0]["app_id"] == app_id
    assert by_id[latest_message["id"]]["resources"] == []


def test_list_chat_messages_restores_resource_cards_by_message_id():
    from app.schemas.app_protocol import LearningResource

    store = get_store()
    suffix = uuid4().hex
    student_id = f"student-resource-restore-{suffix}"
    course_id = f"course-resource-restore-{suffix}"
    conversation_id = f"conversation-resource-restore-{suffix}"
    message_id = f"chatmsg-resource-restore-{suffix}"
    resource = LearningResource(
        resource_id=f"res-resource-restore-{suffix}",
        type="video",
        title="机械振动题目讲解",
        target_topic="机械振动",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVTEST", "bvid": "BVTEST", "description": "机械振动 简谐运动 物理题目讲解"},
        source_refs=[],
        personalized_reason="资源恢复测试",
        tags=["机械振动"],
    )
    store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="test")
    message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="找到一个机械振动视频。",
        message_id=message_id,
    )
    store.create_chat_resource_link(message["id"], resource.resource_id, run_id="run-resource-restore")

    messages = store.list_chat_messages(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        limit=10,
    )

    assert messages[0]["links"] == []
    assert messages[0]["resources"][0]["resource_id"] == resource.resource_id
    assert messages[0]["resources"][0]["title"] == "机械振动题目讲解"


def test_list_chat_messages_restores_resource_cards_by_run_id_to_latest_assistant():
    from app.schemas.app_protocol import LearningResource

    store = get_store()
    suffix = uuid4().hex
    student_id = f"student-resource-run-{suffix}"
    course_id = f"course-resource-run-{suffix}"
    conversation_id = f"conversation-resource-run-{suffix}"
    run_id = f"run-resource-run-{suffix}"
    resource = LearningResource(
        resource_id=f"res-resource-run-{suffix}",
        type="video",
        title="人船模型动量守恒讲解",
        target_topic="人船模型",
        difficulty="adaptive",
        content={"url": "https://www.bilibili.com/video/BVRUN", "bvid": "BVRUN", "description": "人船模型 动量守恒"},
        source_refs=[],
        personalized_reason="运行恢复测试",
        tags=["人船模型"],
    )
    store.save_resource(resource, student_id=student_id, course_id=course_id, created_by_skill="test")
    first_message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="正在搜索。",
        metadata={"run_id": run_id},
        message_id=f"chatmsg-resource-run-first-{suffix}",
    )
    latest_message = store.save_chat_message(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        role="assistant",
        text="搜索完成。",
        metadata={"run_id": run_id},
        message_id=f"chatmsg-resource-run-latest-{suffix}",
    )
    store.create_chat_resource_link(f"msg-stream-resource-{suffix}", resource.resource_id, run_id=run_id)

    messages = store.list_chat_messages(
        student_id=student_id,
        course_id=course_id,
        conversation_id=conversation_id,
        limit=10,
    )

    by_id = {message["id"]: message for message in messages}
    assert by_id[first_message["id"]]["resources"] == []
    assert by_id[latest_message["id"]]["resources"][0]["resource_id"] == resource.resource_id
