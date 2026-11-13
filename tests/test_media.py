"""素材上传：签名计算、请求组装、三步流程、错误处理。

用假的 transport，不起网络。
"""
from __future__ import annotations

import hashlib

import pytest

from qgbot.media import (
    MAX_IMAGE_BYTES,
    MediaError,
    MediaImage,
    build_prepare_body,
    check_size,
    delete_image,
    parse_list_response,
    resolve_content_type,
    upload_image,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


class FakeTransport:
    """记录调用的假 transport。"""

    def __init__(self, *, prepare=None, put_status=200, complete=None, etag=None, delete_status=200):
        self.calls: list[tuple] = []
        self._prepare = prepare or {"upload_id": "up1", "presigned_url": "https://cos/put"}
        self._put_status = put_status
        self._complete = complete or {
            "image_id": "img1",
            "url": "qqbot-media://image/v1/tok",
            "ttl": 7776000,
            "preview_url": "https://cos/preview",
        }
        self._etag = etag
        self._delete_status = delete_status

    async def post_json(self, path, body):
        self.calls.append(("post", path, body))
        if path.endswith("/prepare"):
            return 200, self._prepare
        return 200, self._complete

    async def put_bytes(self, url, data, content_type):
        self.calls.append(("put", url, len(data), content_type))
        etag = self._etag if self._etag is not None else hashlib.md5(data).hexdigest()
        return self._put_status, {"ETag": f'"{etag}"'}

    async def delete(self, path):
        self.calls.append(("delete", path))
        return self._delete_status, {}


class TestContentType:
    @pytest.mark.parametrize("name,mime", [
        ("a.png", "image/png"),
        ("a.jpg", "image/jpeg"),
        ("a.JPEG", "image/jpeg"),
        ("a.gif", "image/gif"),
        ("a.webp", "image/webp"),
    ])
    def test_supported(self, name: str, mime: str) -> None:
        assert resolve_content_type(name) == mime

    def test_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="不支持"):
            resolve_content_type("a.bmp")


class TestSize:
    def test_too_large(self) -> None:
        with pytest.raises(ValueError, match="超过上限"):
            check_size(b"x" * (MAX_IMAGE_BYTES + 1))

    def test_empty(self) -> None:
        with pytest.raises(ValueError, match="为空"):
            check_size(b"")

    def test_ok(self) -> None:
        check_size(b"x" * 1024)


class TestPrepareBody:
    def test_hashes(self) -> None:
        body = build_prepare_body(PNG_BYTES, "card.png")
        assert body["md5"] == hashlib.md5(PNG_BYTES).hexdigest()
        assert body["sha1"] == hashlib.sha1(PNG_BYTES).hexdigest()

    def test_fields(self) -> None:
        body = build_prepare_body(PNG_BYTES, "card.png")
        assert body["file_name"] == "card.png"
        assert body["file_size"] == len(PNG_BYTES)
        assert body["content_type"] == "image/png"


class TestUploadFlow:
    @pytest.mark.asyncio
    async def test_three_steps_in_order(self) -> None:
        t = FakeTransport()
        result = await upload_image(data=PNG_BYTES, file_name="a.png", transport=t)

        assert len(t.calls) == 3
        assert t.calls[0][0] == "post" and t.calls[0][1].endswith("/prepare")
        assert t.calls[1][0] == "put"
        assert t.calls[2][0] == "post" and t.calls[2][1].endswith("/complete")

        assert result.image_id == "img1"
        assert result.url == "qqbot-media://image/v1/tok"

    @pytest.mark.asyncio
    async def test_content_type_matches_prepare(self) -> None:
        """PUT 的 Content-Type 必须和 prepare 声明的一致，否则 COS 返回 403。"""
        t = FakeTransport()
        await upload_image(data=PNG_BYTES, file_name="a.png", transport=t)
        assert t.calls[1][3] == "image/png"

    @pytest.mark.asyncio
    async def test_etag_quotes_stripped(self) -> None:
        """ETag 带引号，去掉才能和 prepare 的 MD5 匹配。"""
        t = FakeTransport(etag="abc123")
        await upload_image(data=PNG_BYTES, file_name="a.png", transport=t)
        complete_body = t.calls[2][2]
        assert complete_body["md5"] == "abc123"

    @pytest.mark.asyncio
    async def test_missing_upload_id(self) -> None:
        t = FakeTransport(prepare={"presigned_url": "https://x"})
        with pytest.raises(MediaError, match="upload_id"):
            await upload_image(data=PNG_BYTES, file_name="a.png", transport=t)

    @pytest.mark.asyncio
    async def test_put_failure(self) -> None:
        t = FakeTransport(put_status=403)
        with pytest.raises(MediaError, match="对象存储"):
            await upload_image(data=PNG_BYTES, file_name="a.png", transport=t)

    @pytest.mark.asyncio
    async def test_list_limit_error_maps_to_chinese(self) -> None:
        """平台错误码要转成能看懂的提示。"""
        class LimitTransport(FakeTransport):
            async def post_json(self, path, body):
                self.calls.append(("post", path, body))
                if path.endswith("/prepare"):
                    return 200, {"upload_id": "up1", "presigned_url": "https://cos/put"}
                return 400, {"code": 40035007, "message": "limit"}

        t = LimitTransport()
        with pytest.raises(MediaError) as exc:
            await upload_image(data=PNG_BYTES, file_name="a.png", transport=t)
        assert "上限" in exc.value.message
        assert exc.value.code == 40035007


class TestMediaImage:
    def test_to_markdown_with_size(self) -> None:
        img = MediaImage(image_id="1", url="qqbot-media://image/v1/tok")
        assert img.to_markdown(400, 300) == "![text #400px #300px](qqbot-media://image/v1/tok)"

    def test_to_markdown_auto(self) -> None:
        img = MediaImage(image_id="1", url="qqbot-media://image/v1/tok")
        assert img.to_markdown_auto() == "![text](qqbot-media://image/v1/tok)"


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_path(self) -> None:
        t = FakeTransport()
        await delete_image(image_id="img42", transport=t)
        assert t.calls[0] == ("delete", "/v2/media-images/img42/delete")

    @pytest.mark.asyncio
    async def test_delete_error(self) -> None:
        t = FakeTransport(delete_status=404)
        with pytest.raises(MediaError):
            await delete_image(image_id="x", transport=t)


class TestParseList:
    def test_parse(self) -> None:
        body = {
            "images": [
                {"image_id": "a", "url": "qqbot-media://image/v1/a", "preview_url": "https://p/a"},
            ],
            "next_cursor": "cur2",
            "total": 1,
        }
        images, cursor = parse_list_response(body)
        assert len(images) == 1
        assert images[0].image_id == "a"
        assert cursor == "cur2"

    def test_empty(self) -> None:
        images, cursor = parse_list_response({})
        assert images == []
        assert cursor == ""
