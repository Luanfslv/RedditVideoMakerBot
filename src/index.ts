import { Container, getContainer } from "@cloudflare/containers";
import { Hono } from "hono";

export class RedditMakerGui extends Container {
  defaultPort = 8080;
  sleepAfter = "1h";
  envVars = {
    FLASK_ENV: "production",
    NEXT_PUBLIC_SUPABASE_URL: "https://cazlmxyjcwqjultcwdqi.supabase.co",
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:
      "sb_publishable_0mTtfZ80iXMv7Xd5CBnh_Q_EJXD5K2t",
    SUPABASE_URL: "https://cazlmxyjcwqjultcwdqi.supabase.co",
    SUPABASE_KEY: "sb_publishable_0mTtfZ80iXMv7Xd5CBnh_Q_EJXD5K2t",
  };

  override onStart() {
    console.log("RedditMaker GUI container started");
  }

  override onStop() {
    console.log("RedditMaker GUI container stopped");
  }

  override onError(error: unknown) {
    console.error("RedditMaker GUI container error:", error);
  }
}

const app = new Hono<{ Bindings: Env }>();

app.all("*", async (c) => {
  const url = new URL(c.req.url);

  // Static assets at the Cloudflare edge — skip the Python container
  if (url.pathname.startsWith("/static/")) {
    const assetPath = url.pathname.slice("/static".length) || "/";
    const assetRequest = new Request(new URL(assetPath, url.origin), c.req.raw);
    const assetResponse = await c.env.ASSETS.fetch(assetRequest);
    if (assetResponse.status !== 404) {
      const headers = new Headers(assetResponse.headers);
      headers.set("Cache-Control", "public, max-age=604800, immutable");
      return new Response(assetResponse.body, {
        status: assetResponse.status,
        headers,
      });
    }
  }

  const container = getContainer(
    c.env.REDDITMAKER_GUI,
    c.env.GUI_CONTAINER_ID || "default",
  );
  return await container.fetch(c.req.raw);
});

export default app;
