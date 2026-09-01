import { cookies } from "next/headers";

const EMPLOYEE_SESSION_COOKIE = "mavi_employee_session";

export async function employeeSessionToken(): Promise<string | undefined> {
  return (await cookies()).get(EMPLOYEE_SESSION_COOKIE)?.value;
}

export async function setEmployeeSessionToken(token: string, expiresAt: string) {
  (await cookies()).set(EMPLOYEE_SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/funcionario",
    expires: new Date(expiresAt),
  });
}

export async function clearEmployeeSessionToken() {
  (await cookies()).delete(EMPLOYEE_SESSION_COOKIE);
}
