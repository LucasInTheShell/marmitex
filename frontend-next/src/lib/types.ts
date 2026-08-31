/** Shared API contracts. The backend remains the source of domain truth. */

export type AccountRole = "company" | "kitchen" | "admin";

export type ProductionStatus =
  | "pending"
  | "printed"
  | "separated"
  | "delivered"
  | "cancelled";

export type KitchenProductionStatus = Exclude<ProductionStatus, "cancelled">;

export type Company = {
  id: string;
  name: string;
  active: boolean;
  created_at: string;
  meal_schedules: MealSchedule[];
};

export type CompanyWithAccess = Company & {
  access_email: string;
};

export type MealSchedule = {
  id: string;
  company_id: string;
  label: string;
  meal_time: string;
  weekdays: number[];
  active: boolean;
  sort_order: number;
};

export type OperationalSettings = {
  order_cutoff_lead_minutes: number;
  updated_at: string;
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
  size_options: SizeOption[];
  price: number | null;
};

export type AvailableMealSchedule = {
  id: string;
  label: string;
  meal_time: string;
  scheduled_for: string;
  cutoff_at: string;
};

export type AvailableMenu = {
  /** ISO date, YYYY-MM-DD */
  date: string;
  items: MenuItem[];
  available_schedules: AvailableMealSchedule[];
};

export type Menu = {
  id: string;
  /** ISO date, YYYY-MM-DD */
  date: string;
  menu_item_ids: string[];
  published: boolean;
};

export type OrderItem = {
  id: string;
  menu_item_id: string;
  item_name: string;
  item_description: string | null;
  size: SizeOption;
  quantity: number;
  unit_price: number;
  subtotal: number;
  notes: string | null;
};

export type Order = {
  id: string;
  order_number: number;
  company_id: string;
  company_name: string;
  date: string;
  meal_schedule_id: string | null;
  meal_schedule_label: string | null;
  scheduled_for: string | null;
  cutoff_at: string | null;
  employee_name: string;
  employee_phone: string;
  employee_department: string;
  employee_cpf: string;
  employee_internal_id: string | null;
  production_status: ProductionStatus;
  total_price: number;
  created_at: string;
  updated_at: string;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  items: OrderItem[];
};

export type KitchenOrder = Omit<
  Order,
  | "employee_phone"
  | "employee_cpf"
  | "cutoff_at"
  | "total_price"
  | "cancelled_at"
  | "cancellation_reason"
>;

export type OrderCreateItem = {
  menu_item_id: string;
  size: SizeOption;
  quantity: number;
  notes?: string | null;
};

export type OrderCreatePayload = {
  date: string;
  meal_schedule_id: string;
  employee_name: string;
  employee_phone: string;
  employee_department: string;
  employee_cpf: string;
  employee_internal_id?: string | null;
  items: OrderCreateItem[];
};

export type ProductionSizeSummary = {
  size: SizeOption;
  quantity: number;
};

export type ProductionItemSummary = {
  menu_item_id: string;
  item_name: string;
  total_quantity: number;
  sizes: ProductionSizeSummary[];
};

export type MealTimeProductionSummary = {
  scheduled_for: string | null;
  meal_time: string | null;
  schedule_ids: string[];
  schedule_labels: string[];
  total_orders: number;
  total_meals: number;
  items: ProductionItemSummary[];
};

export type CompanyMealTimeProductionSummary = {
  scheduled_for: string | null;
  meal_time: string | null;
  total_orders: number;
  total_meals: number;
};

export type CompanyProductionSummary = {
  company_id: string;
  company_name: string;
  total_orders: number;
  total_meals: number;
  meal_times: CompanyMealTimeProductionSummary[];
  items: ProductionItemSummary[];
};

export type DailyProductionSummary = {
  date: string;
  total_orders: number;
  total_meals: number;
  meal_times: MealTimeProductionSummary[];
  companies: CompanyProductionSummary[];
};

export const SIZE_OPTIONS = ["P", "M", "G"] as const;
export type SizeOption = (typeof SIZE_OPTIONS)[number];
