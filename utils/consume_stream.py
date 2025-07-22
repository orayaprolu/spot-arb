async def consume_stream(feed):
  '''just drain stream_bba so feed._bba stays fresh'''
  async for _ in feed.stream_bba():
    pass
