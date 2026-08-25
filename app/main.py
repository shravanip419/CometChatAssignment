import sys
import argparse
from app.agent.agent import SupportAgent
from app.config import DEBUG_MODE


def run_cli():
    parser = argparse.ArgumentParser(description="Aster & Row AI Customer Support Agent")
    parser.add_argument("--query", "-q", type=str, help="Single query to process")
    parser.add_argument("--session", "-s", type=str, default="cli-session", help="Session ID")
    parser.add_argument("--debug", "-d", action="store_true", default=DEBUG_MODE, help="Enable debug trace output")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive multi-turn chat session")

    args = parser.parse_args()
    agent = SupportAgent(debug=args.debug)

    if args.query:
        response = agent.process_message(args.query, session_id=args.session)
        print("\n--- Aster & Row Support Agent Response ---")
        print(f"Answer:\n{response.answer}\n")
        if response.sources:
            print("Sources:")
            for src in response.sources:
                print(f"  - [{src.filename} - {src.heading}]")
        print(f"Human Handoff Recommended: {response.handoff}")
        if response.tool_called:
            print(f"Tool Called: {response.tool_called}")
        if args.debug and response.debug_info:
            import pprint
            print("\n[DEBUG TRACE]")
            pprint.pprint(response.debug_info)
        return

    if args.interactive or len(sys.argv) == 1:
        print("=" * 60)
        
        print(" Aster & Row Customer Support Agent (Interactive CLI)")
        print(" Type 'exit', 'quit', or 'q' to end session.")
        print("=" * 60)
        session_id = args.session
        while True:
            try:
                user_input = input("\nCustomer > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    print("Goodbye!")
                    break
                response = agent.process_message(user_input, session_id=session_id)
                print(f"\nAgent > {response.answer}")
                if response.sources:
                    print("Sources:", ", ".join(f"[{s.filename} - {s.heading}]" for s in response.sources))
                if response.handoff:
                    print("[Human Handoff Flag: True]")
                if args.debug and response.debug_info:
                    import pprint
                    print("\n[DEBUG TRACE]")
                    pprint.pprint(response.debug_info)
            except (KeyboardInterrupt, EOFError):
                print("\nSession ended.")
                break


if __name__ == "__main__":
    run_cli()
