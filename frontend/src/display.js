const analystDisplayNames = {
  "demo-admin": "Admin",
};

export function displayUsername(username) {
  if (!username) return username;
  return analystDisplayNames[String(username).toLowerCase()] || username;
}
