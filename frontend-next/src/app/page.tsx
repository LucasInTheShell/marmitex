import { redirect } from "next/navigation";

import { currentAccount, homePathFor } from "@/lib/auth";

export default async function RootPage() {
  const account = await currentAccount();
  redirect(account ? homePathFor(account.role) : "/login");
}
