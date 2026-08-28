/** Shared API contracts. The backend remains the source of domain truth. */

export type AccountRole = "company" | "kitchen" | "admin";

export type ProductionStatus = "pending" | "printed" | "separated" | "delivered";

export type Company = {
  id: string;
  name: string;
  active: boolean;
  created_at: string;
};

export type CompanyWithAccess = Company & {
  access_email: string;
};

export type Account = {
  id: string;
  name: string;
  email: string;
  company_id: string | null;
  role: AccountRole;
};

export type MenuItem = {
  id: string;
  name: string;
  description: string | null;
  size_options: string[];
  price: number | null;
};

export type Menu = {
  id: string;
  /** ISO date, YYYY-MM-DD */
  date: string;
  menu_item_ids: string[];
  published: boolean;
};

export const SIZE_OPTIONS = ["P", "M", "G"] as const;
