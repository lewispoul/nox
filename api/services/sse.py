import asyncio

from starlette.responses import StreamingResponse


async def sse_event_generator(log_iter, heartbeat=15):
    try:
        while True:
            line = next(log_iter, None)
            if line is not None:
                yield f"data: {line}\n\n"
            else:
                await asyncio.sleep(heartbeat)
                yield ": keep-alive\n\n"
    except StopIteration:
        return


def sse_response(log_iter, heartbeat=15):
    return StreamingResponse(
        sse_event_generator(log_iter, heartbeat),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
