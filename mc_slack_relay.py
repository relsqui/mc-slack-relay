import asyncio
import os
import re
import sys
from aioconsole import ainput
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

slack_app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# include_pattern = '\[\d\d:\d\d:\d\d] \[Server thread/INFO] \[minecraft/MinecraftServer\]: '
# exclude_pattern = f"{include_pattern}\[Slack] "
# relay_pattern = f"{include_pattern}(.*)"

include_pattern = '.'
exclude_pattern = '.* \[Slack] '
relay_pattern = '(.*)'
slack_channel = os.environ["SLACK_CHANNEL_ID"]

input_queue = asyncio.Queue()

async def slack_connection():
  """Manage the socket with Slack."""
  slack_handler = AsyncSocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])
  try:
    await slack_handler.start_async()
  except asyncio.CancelledError:
    await slack_handler.close_async()
    raise

async def slack_post(message):
  """Post a message into the Slack channel."""
  await slack_app.client.chat_postMessage(
    channel=slack_channel,
    text=message
  )

@slack_app.message()
async def slack_listener(message):
  """Read messages from the Slack channel into the input queue."""
  username = (await slack_app.client.users_info(user=message['user']))['user']['name']
  await input_queue.put(f"say [Slack] <@{username}> {message['text']}")

async def server_listener(subproc):
  """Print the server's output, and relay some of it into Slack."""
  while subproc.returncode is None:
    line_bytes = await subproc.stdout.readline()
    if len(line_bytes) == 0:
      break
    line = line_bytes.decode().strip()
    print(line)

    # should we send this one to Slack too?
    if not re.match(include_pattern, line):
      continue
    if re.match(exclude_pattern, line):
      continue
    relay_match = re.match(relay_pattern, line)
    if relay_match is None:
      continue
    to_relay = relay_match.group(1)
    if to_relay is None:
      continue
    await slack_post(to_relay)

async def server_input(subproc):
  """Read from the input queue into the actual server input."""
  while subproc.returncode is None:
    nextInput = await input_queue.get()
    subproc.stdin.write(f"{nextInput}\n".encode())

async def user_listener():
  """Read keyboard input into the input queue."""
  while True:
    userInput = await ainput()
    await input_queue.put(userInput)

async def main():
  """Start the server and manage all the attendant listeners."""
  subproc = await asyncio.create_subprocess_exec(
    'bash',
    './chatter.sh',
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE
    # TODO: don't drop stderr! (although it does get logged anyway)
  )
  
  # schedule the listeners in the event loop
  tasks = []
  for coro in [server_input(subproc), user_listener(), slack_connection()]:
    tasks.append(asyncio.create_task(coro))

  # interact with the server until it stops
  await server_listener(subproc)

  for task in tasks:
    task.cancel()
  # give them time to finish cleaning up
  await asyncio.wait(tasks)

if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    sys.exit(0)
