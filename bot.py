"""
Discord bot for image generation via Qwen (Tongyi Wanxiang / DashScope) API.

Slash command:
    /imagine prompt:<text> [negative_prompt] [size] [steps]

Set your credentials in a .env file (see .env.example) or as environment variables:
    DISCORD_TOKEN   - your Discord bot token
    QWEN_API_KEY    - your DashScope / Qwen API key
"""

import asyncio
import io
import logging
import os

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

# DashScope (Alibaba Cloud) endpoints for Qwen/Wanxiang image generation.
# Docs: https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-wanxiang
QWEN_CREATE_TASK_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
)
QWEN_TASK_STATUS_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("qwen-discord-bot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


async def submit_generation_task(
    session: aiohttp.ClientSession,
    prompt: str,
    negative_prompt: str | None,
    size: str,
) -> str:
    """Submit an async image-generation task to Qwen/Wanxiang and return its task_id."""
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": "wanx2.1-t2i-turbo",
        "input": {
            "prompt": prompt,
            **({"negative_prompt": negative_prompt} if negative_prompt else {}),
        },
        "parameters": {
            "size": size,
            "n": 1,
        },
    }

    async with session.post(QWEN_CREATE_TASK_URL, json=payload, headers=headers) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise RuntimeError(f"Qwen API error ({resp.status}): {data}")
        return data["output"]["task_id"]


async def poll_task(
    session: aiohttp.ClientSession,
    task_id: str,
    timeout: float = 120.0,
    interval: float = 2.0,
) -> str:
    """Poll the task until it succeeds and return the resulting image URL."""
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}"}
    url = QWEN_TASK_STATUS_URL.format(task_id=task_id)
    elapsed = 0.0

    while elapsed < timeout:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            status = data["output"]["task_status"]

            if status == "SUCCEEDED":
                results = data["output"]["results"]
                if not results:
                    raise RuntimeError("Task succeeded but returned no images.")
                return results[0]["url"]
            if status in ("FAILED", "UNKNOWN"):
                raise RuntimeError(f"Qwen task failed: {data['output']}")

        await asyncio.sleep(interval)
        elapsed += interval

    raise TimeoutError("Timed out waiting for Qwen image generation.")


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        log.info("Synced %d command(s)", len(synced))
    except Exception:
        log.exception("Failed to sync commands")
    log.info("Logged in as %s (id: %s)", bot.user, bot.user.id)


@bot.tree.command(name="imagine", description="Generate an image with Qwen from your prompt")
@app_commands.describe(
    prompt="What you want the image to show",
    negative_prompt="Things to avoid in the image (optional)",
    size="Image size, e.g. 1024*1024, 1280*720 (optional)",
)
async def imagine(
    interaction: discord.Interaction,
    prompt: str,
    negative_prompt: str | None = None,
    size: str = "1024*1024",
):
    if not QWEN_API_KEY:
        await interaction.response.send_message(
            "QWEN_API_KEY is not configured on the server.", ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    try:
        async with aiohttp.ClientSession() as session:
            task_id = await submit_generation_task(session, prompt, negative_prompt, size)
            image_url = await poll_task(session, task_id)

            async with session.get(image_url) as img_resp:
                image_bytes = await img_resp.read()

        file = discord.File(io.BytesIO(image_bytes), filename="generated.png")
        embed = discord.Embed(title="Generated image", description=f"**Prompt:** {prompt}")
        embed.set_image(url="attachment://generated.png")
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, file=file)

    except TimeoutError:
        await interaction.followup.send("Generation timed out, please try again.")
    except Exception as exc:
        log.exception("Generation failed")
        await interaction.followup.send(f"Something went wrong: {exc}")


def main():
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN is not set. Add it to your .env file.")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
