export async function sendQuestion(query) {
  const response = await fetch("/api/chat/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, limit: 3 }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.query?.[0] ||
      "The request failed. Check that Django is running.";

    throw new Error(message);
  }

  if (typeof data?.answer !== "string" || !Array.isArray(data?.sources)) {
    throw new Error("The server returned an unexpected response.");
  }

  return data;
}