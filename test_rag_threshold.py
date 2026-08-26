import asyncio
import sys
sys.path.insert(0, 'backend')
from app.rag.retriever import search_transcripts

async def main():
    print("=== Testing Query 1: 'how to bake chocolate cake' (Unrelated) ===")
    res_cake = await search_transcripts("how to bake chocolate cake")
    print(f"Total returned: {len(res_cake)}")
    for r in res_cake:
        print(f"  Similarity: {r['similarity']:.4f} | Episode: {r['episode'][:35]} | Excerpt: {r['excerpt'][:60]}...")

    print("\n=== Testing Query 2: 'LNO framework Shreyas Doshi' (Highly Relevant) ===")
    res_lno = await search_transcripts("LNO framework Shreyas Doshi")
    print(f"Total returned: {len(res_lno)}")
    for r in res_lno:
        print(f"  Similarity: {r['similarity']:.4f} | Episode: {r['episode'][:35]} | Excerpt: {r['excerpt'][:60]}...")

if __name__ == "__main__":
    asyncio.run(main())
