import asyncio
import json
from typing import Optional

import aiohttp
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify

from .converter import ImageFinder


class OCR(commands.Cog):
    """Detect text in images using ocr.space or Google Cloud Vision API."""

    __authors__ = "Authors: <@306810730055729152>, TrustyJAID"
    __version__ = "Cog Version: 0.3.3"

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\n{self.__authors__}\n{self.__version__}"

    def __init__(self, bot: Red):
        self.bot = bot
        self.sussy_string = "7d3306461d88957"
        self.session = aiohttp.ClientSession()

    def cog_unload(self) -> None:
        asyncio.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs) -> None:
        """Nothing to delete"""
        pass

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(read_message_history=True)
    async def freeocr(self, ctx: commands.Context, *, image: ImageFinder = None):
        """Detect text in an image through ocr.space API.

        This usually gives poor or subpar results for non latin text in images.
        This also assumes the text in image will be in English language.
        """
        await ctx.trigger_typing()
        if image is None:
            if ctx.message.reference:
                message = ctx.message.reference.resolved
                image = await ImageFinder().find_images_in_replies(message)
            else:
                image = await ImageFinder().search_for_images(ctx)
        if not image:
            return await ctx.send("No images or direct image links were detected. 😢")
        await self._free_ocr(ctx, image[0])

    async def _free_ocr(self, ctx: commands.Context, image: str):
        file_type = image.split(".").pop().upper()
        data = {
            "url": image,
            "apikey": self.sussy_string,
            "language": "eng",
            "isOverlayRequired": False,
            "filetype": file_type
        }
        try:
            async with self.session.get(
                "https://api.kaogurai.xyz/v1/ocr/image",
                params={"url": image},
            ) as resp:
                if resp.status != 200:
                    return await ctx.send(f"https://http.cat/{resp.status}")
                result = await resp.json()
        except Exception:
            async with self.session.post(
                "https://api.ocr.space/parse/image", data=data
            ) as resp:
                if resp.status != 200:
                    return await ctx.send(f"https://http.cat/{resp.status}")
                result = await resp.json()

        temp_ = result.get("textAnnotations", [{}])
        if temp_ and temp_[0].get("description"):
            return await ctx.send_interactive(
                pagify(temp_[0].get("description", "none")), box_lang=""
            )
        if not result.get("ParsedResults"):
            return await ctx.send(box(json.dumps(result), "json"))

        return await ctx.send(result["ParsedResults"][0].get("ParsedText"))

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(read_message_history=True)
    async def ocr(
        self,
        ctx: commands.Context,
        detect_handwriting: Optional[bool] = False,
        *,
        image: ImageFinder = None,
    ):
        """Detect text in an image through Google OCR API.

        You may use it to run OCR on old messages which contains attachments/image links.
        Simply reply to the said message with `[p]ocr` for detection to work.
        """
        api_key = (await ctx.bot.get_shared_api_tokens("google_vision")).get("api_key")

        await ctx.trigger_typing()
        if image is None:
            if ctx.message.reference:
                message = ctx.message.reference.resolved
                image = await ImageFinder().find_images_in_replies(message)
            else:
                image = await ImageFinder().search_for_images(ctx)
        if not image:
            return await ctx.send("No images or direct image links were detected. 😢")

        if not api_key:
            return await self._free_ocr(ctx, image[0])
        base_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        detect_type = "DOCUMENT_TEXT_DETECTION" if detect_handwriting else "TEXT_DETECTION"
        payload = {
            "requests": [
                {
                    "image": {"source": {"imageUri": image[0]}},
                    "features": [{"type": detect_type}],
                }
            ]
        }

        try:
            async with self.session.post(base_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    return await ctx.send(f"https://http.cat/{response.status}")
                data = await response.json()
        except asyncio.TimeoutError:
            return await ctx.send("Operation timed out.")

        output = data.get("responses")
        if output is None or output[0] == {}:
            return await ctx.send("No text detected.")
        if output[0].get("error") and output[0].get("error").get("message"):
            return await ctx.send(
                f"API returned error: {output[0]['error']['message']}"
            )
        detected_text = output[0].get("textAnnotations")[0].get("description")
        if not detected_text:
            return await ctx.send("No text was detected in the target image.")

        await ctx.send_interactive(pagify(detected_text), box_lang="")
