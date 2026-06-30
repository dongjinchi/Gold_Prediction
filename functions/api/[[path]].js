// Cloudflare Pages Function — API 代理到 Railway
// 浏览器 → Cloudflare → Railway，解决国内访问 Railway 网络不通的问题

export async function onRequest(context) {
  const { request, params } = context;
  const url = new URL(request.url);
  const path = params.path || '';
  const search = url.search || '';

  const target = `https://web-production-536ee.up.railway.app/api/${path}${search}`;

  try {
    const resp = await fetch(target, {
      method: request.method,
      headers: request.headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.arrayBuffer() : undefined,
    });

    // SSE 需要流式转发
    if (resp.headers.get('content-type')?.includes('text/event-stream')) {
      return new Response(resp.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    const body = await resp.arrayBuffer();
    return new Response(body, {
      status: resp.status,
      headers: {
        'Content-Type': resp.headers.get('content-type') || 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: '后端暂不可用，请稍后重试' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }
}
