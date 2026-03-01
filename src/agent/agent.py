"""
Conversational AI agent backed by OpenAI with function-calling tools
for cryptocurrency market data.
"""

import json
import os
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv
from src.agent.tools import TOOL_SCHEMAS, call_tool

load_dotenv()


def _build_system_prompt() -> str:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return f"""\
You are **Crypto Market Agent**, a helpful assistant that answers questions
about cryptocurrency market-cap rankings, prices, and volumes.
Today's date is {today}.

## Capabilities
- Retrieve the top N coins (excluding stablecoins) at the START and/or END
  of any calendar quarter.
- Look up a single coin's price, market cap, and 24-h volume on any date.

## Important rules about dates
- You can query ANY date the user asks for — past, present, or future.
- Do NOT refuse a request based on date. ALWAYS call the tool first.
- If CoinGecko has no data for a date (e.g. a future date), the tool will
  return an error and you should relay that to the user politely.

## Column filtering
- The full set of available columns is: date, symbol, name, price, market_cap, volume
- When the user says they only want certain columns (e.g. "only date, price and market cap"),
  pass EXACTLY those column names in the "columns" parameter.
- If the user doesn't mention specific columns, omit the columns parameter (returns all).
- Map user language to column names:
  "price" → "price", "market cap" → "market_cap", "volume" → "volume",
  "date" → "date", "symbol"/"ticker" → "symbol", "name"/"coin name" → "name"

## CSV export
- When the user asks to download, export, save as CSV, or wants a file,
  set "export_csv" to true in the tool call.
- The tool will save a CSV file and return the file path.
- Tell the user the FULL file path so they can find it.

## Formatting rules
- Present tabular data as a **Markdown table**.
- Only show the columns the user requested (or all if unspecified).
- Format prices with commas and 2 decimal places.
- Format market cap and volume in billions/millions for readability
  (e.g. $1.23 T, $456.7 B, $12.3 M).
- When data spans many dates (more than ~30 rows), summarise first and
  offer to show more.
- When the user says "beginning" or "start" of a quarter → position = "start".
- When the user says "end" of a quarter → position = "end".
- Default to top 15, position "end", from 2020 unless told otherwise.
- Always exclude stablecoins.

## Behaviour
- Be concise but informative.
- If a query is ambiguous, make reasonable assumptions and state them.
- If the data fetch will take a while, mention that upfront.
"""


class CryptoAgent:
    """Stateful chat agent with tool-calling loop."""

    def __init__(self, model: str = "gpt-4o"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.messages: list[dict] = [
            {"role": "system", "content": _build_system_prompt()}
        ]

    def chat(self, user_message: str) -> str:
        """Send *user_message*, handle tool calls, return final text."""
        self.messages.append({"role": "user", "content": user_message})

        while True:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            msg = resp.choices[0].message

            # No tool calls → final answer
            if not msg.tool_calls:
                text = msg.content or ""
                self.messages.append({"role": "assistant", "content": text})
                return text

            # Process every tool call
            self.messages.append(msg)
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                print(f"  🔧  {fn_name}({json.dumps(fn_args, indent=2)})")
                result = call_tool(fn_name, fn_args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

    def reset(self):
        """Clear conversation history (keeps system prompt)."""
        self.messages = [
            {"role": "system", "content": _build_system_prompt()}
        ]
