"""
CLI entry point.

Run with:
    python -m src.main
"""

from src.agent.agent import CryptoAgent


def main():
    try:
        agent = CryptoAgent()
    except ValueError as e:
        print(f"\n❌  Failed to start: {e}")
        print("   Make sure OPENAI_API_KEY is set in your .env file.")
        return

    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🪙  Crypto Market Agent                                ║")
    print("║  Ask about top coins, quarterly rankings, prices…       ║")
    print("║  You can filter columns & export to CSV!                ║")
    print("║  Type 'quit' to exit  |  'reset' to clear history      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("  Examples:")
    print("  • Top 15 crypto, only date price and market cap, from 2024")
    print("  • Top 10 coins at end of Q4 2024, export as CSV")
    print("  • Bitcoin price on 2024-06-30, download CSV")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye! 👋")
            break
        if user_input.lower() == "reset":
            agent.reset()
            print("🔄 Conversation reset.\n")
            continue

        print()
        answer = agent.chat(user_input)
        print(f"\nAgent:\n{answer}\n")


if __name__ == "__main__":
    main()
