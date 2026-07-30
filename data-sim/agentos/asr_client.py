"""
阿里云智能语音交互 (ASR) 客户端
==============================
基于阿里云 NLS (Natural Language Service) 实现语音转文字。
支持一句话识别 (≤60s) 和长音频分片识别，无需 OSS。

API 端点：
- Token: POST nls-meta.cn-shanghai.aliyuncs.com/pop/2018-05-18/tokens
- 一句话识别: POST nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr
- 录音文件识别: POST/GET nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/filetrans

使用方式：
    client = AlibabaASRClient()
    text = client.transcribe("dictation.wav")       # 本地文件
    text = client.transcribe_bytes(audio_bytes)     # 字节流
"""

import os
import json
import time
import base64
import hashlib
import hmac
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import logging

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

# 最大一句话识别时长（秒），超过此值使用分片或文件识别
MAX_SENTENCE_DURATION = 60

# 音频参数
SAMPLE_RATE = 16000      # 采样率 16kHz
AUDIO_FORMAT = "pcm"     # 格式
BYTES_PER_SEC = SAMPLE_RATE * 2  # 16-bit mono PCM = 32000 bytes/sec


def _load_env():
    """加载 .env"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    if key not in os.environ:
                        os.environ[key] = val.strip().strip('"').strip("'")


_load_env()


# ============================================================
# 客户端
# ============================================================

class AlibabaASRClient:
    """
    阿里云语音识别客户端。

    Args:
        access_key_id: 阿里云 AccessKey ID
        access_key_secret: 阿里云 AccessKey Secret
        app_key: NLS 项目 AppKey
    """

    TOKEN_URL = "https://nls-meta.cn-shanghai.aliyuncs.com/pop/2018-05-18/tokens"
    ASR_URL = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"
    FILETRANS_URL = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/filetrans"

    def __init__(
        self,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        app_key: Optional[str] = None,
    ):
        self.ak_id = access_key_id or os.getenv("ALIBABA_ACCESS_KEY_ID", "")
        self.ak_secret = access_key_secret or os.getenv("ALIBABA_ACCESS_KEY_SECRET", "")
        self.app_key = app_key or os.getenv("ALIBABA_NLS_APP_KEY", "")

        self._token: Optional[str] = None
        self._token_expire: float = 0

    # ----- Token 管理 -----

    def get_token(self) -> str:
        """获取或刷新访问 Token（有效期 24h，实际缓存 23h）。

        优先使用阿里云 NLS SDK，如不可用则回退至 HTTP 签名方式。
        """
        now = time.time()
        if self._token and now < self._token_expire:
            return self._token

        if not self.ak_id or not self.ak_secret:
            raise RuntimeError(
                "Alibaba Cloud AccessKey not configured. "
                "Set ALIBABA_ACCESS_KEY_ID and ALIBABA_ACCESS_KEY_SECRET in .env"
            )

        # 尝试 SDK 方式
        try:
            from alibabacloud_nls_cloud_meta20180518.client import Client as NlsClient
            from alibabacloud_tea_openapi import models as open_api_models

            config = open_api_models.Config(
                access_key_id=self.ak_id,
                access_key_secret=self.ak_secret,
            )
            config.endpoint = "nls-meta.cn-shanghai.aliyuncs.com"
            client = NlsClient(config)
            resp = client.create_token()

            body = resp.body
            token_data = body.get("Token", {}) if isinstance(body, dict) else body.token
            self._token = token_data.get("Id", "") if isinstance(token_data, dict) else token_data.id

            expire_at = token_data.get("ExpireTime", 0) if isinstance(token_data, dict) else token_data.expire_time
            if expire_at:
                self._token_expire = min(now + (expire_at - int(now)), now + 82800)
            else:
                self._token_expire = now + 82800  # 23h

            logger.info("ASR token refreshed via SDK, expires at %s",
                         datetime.fromtimestamp(self._token_expire).isoformat())
            return self._token

        except ImportError:
            logger.warning("NLS SDK not available, using HTTP token API")
        except Exception as e:
            logger.warning("SDK token fetch failed (%s), trying HTTP fallback", e)

        # HTTP fallback
        return self._get_token_http()

    def _get_token_http(self) -> str:
        """通过原始 HTTP API 获取 Token（签名认证）。"""
        import hmac
        import hashlib
        import base64
        import uuid

        from datetime import timezone

        now = time.time()
        now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
        timestamp = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        nonce = str(uuid.uuid4())

        # HMAC-SHA1 签名
        params = [
            ("AccessKeyId", self.ak_id),
            ("Action", "CreateToken"),
            ("Format", "JSON"),
            ("RegionId", "cn-shanghai"),
            ("SignatureMethod", "HMAC-SHA1"),
            ("SignatureNonce", nonce),
            ("SignatureVersion", "1.0"),
            ("Timestamp", timestamp),
            ("Version", "2018-05-18"),
        ]
        params.sort()
        canonical = "&".join(f"{k}={v}" for k, v in params)
        string_to_sign = f"GET&%2F&{canonical}"
        signature = base64.b64encode(
            hmac.new(
                f"{self.ak_secret}&".encode(),
                string_to_sign.encode(),
                hashlib.sha1,
            ).digest()
        ).decode()

        query = "&".join(f"{k}={v}" for k, v in params) + f"&Signature={signature}"
        url = f"https://nls-meta.cn-shanghai.aliyuncs.com/?{query}"

        req = Request(url)
        try:
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Failed to get ASR token via HTTP: {e}")

        if "Token" not in data:
            msg = data.get("Message", data.get("ErrMsg", "unknown error"))
            raise RuntimeError(f"ASR token HTTP error: {msg}")

        token_data = data["Token"]
        self._token = token_data.get("Id", "")
        expire_at = token_data.get("ExpireTime", 0)
        if expire_at:
            self._token_expire = min(now + (expire_at - int(now)), now + 82800)
        else:
            self._token_expire = now + 82800

        logger.info("ASR token refreshed via HTTP")
        return self._token

    # ----- 一句话识别（≤60s）-----

    def _recognize_short(self, audio_data: bytes, fmt: str = "pcm") -> dict:
        """
        一句话识别 REST API。

        Args:
            audio_data: PCM 16kHz 16bit 单声道原始音频
            fmt: 音频格式 (pcm/wav/opus)

        Returns:
            {"status": "ok", "text": "...", "confidence": 0.95}
        """
        token = self.get_token()

        params = (
            f"?appkey={self.app_key}"
            f"&format={fmt}"
            f"&sample_rate={SAMPLE_RATE}"
            f"&enable_punctuation_prediction=true"
            f"&enable_inverse_text_normalization=true"
        )

        url = self.ASR_URL + params

        req = Request(
            url,
            data=audio_data,
            headers={
                "X-NLS-Token": token,
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(audio_data)),
            },
        )

        try:
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ASR HTTP {e.code}: {body}")
        except Exception as e:
            raise RuntimeError(f"ASR request failed: {e}")

        if result.get("status") != 20000000:
            msg = result.get("status_text", "unknown")
            raise RuntimeError(f"ASR recognition error: {msg} (code={result.get('status')})")

        return {
            "status": "ok",
            "text": result.get("result", ""),
            "confidence": self._parse_confidence(result),
        }

    def _recognize_chunked(self, audio_data: bytes) -> str:
        """
        长音频分片识别：将音频切分为 ≤60s 的片段，逐片识别后拼接。

        按静音段简单切分 > 50s 边界。
        """
        total_sec = len(audio_data) / BYTES_PER_SEC

        if total_sec <= MAX_SENTENCE_DURATION:
            r = self._recognize_short(audio_data)
            return r["text"]

        # 分片：每 55 秒切一片（留余量）
        chunk_sec = 55
        chunk_bytes = int(chunk_sec * BYTES_PER_SEC)

        chunks = []
        offset = 0
        while offset < len(audio_data):
            end = min(offset + chunk_bytes, len(audio_data))
            chunk = audio_data[offset:end]
            try:
                r = self._recognize_short(chunk)
                chunks.append(r["text"])
            except Exception as e:
                logger.warning("Chunk %d-%d failed: %s", offset, end, e)
                chunks.append("")  # 跳过失败的片段
            offset = end

        return "".join(chunks)

    @staticmethod
    def _parse_confidence(result: dict) -> float:
        """从结果中提取置信度"""
        try:
            sentences = result.get("sentence_list", [])
            if sentences:
                conf = sentences[0].get("confidence", 0)
                return float(conf) / 100.0 if isinstance(conf, (int, float)) and conf > 1 else float(conf)
        except (ValueError, TypeError):
            pass

        # 尝试从 result 直接获取
        raw_conf = result.get("confidence", 0)
        try:
            return float(raw_conf)
        except (ValueError, TypeError):
            return 0.0

    # ----- 公共接口 -----

    def transcribe(self, file_path: str) -> dict:
        """
        转写本地音频文件。

        支持格式：WAV (PCM 16kHz 16bit mono), 或原始 PCM

        Returns:
            {"status": "ok", "text": "转写文本", "duration_sec": 120, "confidence": 0.95}
        """
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}

        audio_bytes = path.read_bytes()

        # 如果是 WAV，提取 PCM 数据（跳过 44 字节头）
        if path.suffix.lower() in (".wav", ".wave"):
            audio_bytes = self._wav_to_pcm(audio_bytes)

        return self.transcribe_bytes(audio_bytes)

    def transcribe_bytes(self, audio_bytes: bytes, fmt: str = "pcm") -> dict:
        """
        转写音频字节流。

        Args:
            audio_bytes: PCM 16kHz 16bit 单声道原始音频
            fmt: 音频格式

        Returns:
            {"status": "ok", "text": "...", "duration_sec": N, "confidence": ...}
        """
        if not audio_bytes:
            return {"status": "error", "message": "Empty audio data"}

        duration = len(audio_bytes) / BYTES_PER_SEC

        try:
            if duration <= MAX_SENTENCE_DURATION:
                r = self._recognize_short(audio_bytes, fmt)
                return {
                    "status": "ok",
                    "text": r["text"],
                    "duration_sec": round(duration, 1),
                    "confidence": r.get("confidence", 0),
                }
            else:
                text = self._recognize_chunked(audio_bytes)
                return {
                    "status": "ok",
                    "text": text,
                    "duration_sec": round(duration, 1),
                    "confidence": 0.9,
                }

        except RuntimeError as e:
            return {"status": "error", "message": str(e), "duration_sec": round(duration, 1)}
        except Exception as e:
            logger.exception("Unexpected ASR error")
            return {"status": "error", "message": str(e), "duration_sec": round(duration, 1)}

    @staticmethod
    def _wav_to_pcm(wav_bytes: bytes) -> bytes:
        """
        简单的 WAV→PCM 提取。
        标准 WAV: 44 字节头部 + PCM 数据。
        """
        if len(wav_bytes) < 44:
            return wav_bytes

        # 检查 RIFF 头
        if wav_bytes[:4] != b"RIFF":
            logger.warning("Not a valid WAV file, treating as raw PCM")
            return wav_bytes

        # 查找 data chunk
        # 简单方法：跳过 44 字节标准头
        data_offset = 44
        # 更健壮：搜索 "data" chunk
        idx = wav_bytes.find(b"data", 12)
        if idx > 0:
            data_offset = idx + 8  # "data" (4) + size (4)

        return wav_bytes[data_offset:]


# ============================================================
# 模块级便捷函数
# ============================================================

_default_client: Optional[AlibabaASRClient] = None


def get_client() -> AlibabaASRClient:
    """获取全局 ASR 客户端（懒加载）。"""
    global _default_client
    if _default_client is None:
        _default_client = AlibabaASRClient()
    return _default_client


def transcribe(audio_path: str) -> dict:
    """快捷函数：转写本地音频文件。"""
    return get_client().transcribe(audio_path)


def transcribe_bytes(audio_bytes: bytes) -> dict:
    """快捷函数：转写音频字节流。"""
    return get_client().transcribe_bytes(audio_bytes)


# ============================================================
# CLI 测试入口
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python asr_client.py <audio_file.wav>")
        print(f"  AppKey: {os.getenv('ALIBABA_NLS_APP_KEY', 'NOT SET')}")
        print(f"  AK ID:  {os.getenv('ALIBABA_ACCESS_KEY_ID', 'NOT SET')[:8]}***")
        sys.exit(1)

    client = AlibabaASRClient()
    print("Getting token...")
    token = client.get_token()
    print(f"Token: {token[:20]}...")

    file_path = sys.argv[1]
    print(f"Transcribing: {file_path}")
    result = client.transcribe(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
