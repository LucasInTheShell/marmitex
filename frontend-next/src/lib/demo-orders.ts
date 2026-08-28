import type { ProductionStatus } from "@/lib/types";

export type DemoOrder = {
  id: string;
  companyId: string;
  companyName: string;
  date: string;
  menuItemId: string;
  menuItemName: string;
  size: "P" | "M" | "G";
  employeeName: string;
  employeePhone: string;
  employeeDepartment: string;
  employeeCpf: string;
  productionStatus: ProductionStatus;
  createdAt: string;
};

export type DemoMenuItem = {
  id: string;
  name: string;
  description: string;
  price: number;
  accent: string;
};

export const DEMO_MENU_ITEMS: DemoMenuItem[] = [
  {
    id: "frango-grelhado",
    name: "Frango grelhado",
    description: "Arroz, feijão, legumes assados e salada fresca",
    price: 24.9,
    accent: "bg-emerald-500",
  },
  {
    id: "picadinho-carne",
    name: "Picadinho de carne",
    description: "Arroz, feijão, farofa crocante e couve refogada",
    price: 27.5,
    accent: "bg-amber-500",
  },
  {
    id: "vegetariano",
    name: "Bowl vegetariano",
    description: "Arroz integral, grão-de-bico, abóbora e folhas",
    price: 23.9,
    accent: "bg-sky-500",
  },
];

export const PRODUCTION_STATUS: Array<{
  value: ProductionStatus;
  label: string;
  shortLabel: string;
}> = [
  { value: "pending", label: "Pedido recebido", shortLabel: "Recebido" },
  { value: "printed", label: "Etiqueta impressa", shortLabel: "Impresso" },
  { value: "separated", label: "Pedido separado", shortLabel: "Separado" },
  { value: "delivered", label: "Pedido entregue", shortLabel: "Entregue" },
];

export function localIsoDate(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function addCalendarDays(date: string, amount: number): string {
  const [year, month, day] = date.split("-").map(Number);
  const result = new Date(year, month - 1, day + amount);
  return localIsoDate(result);
}

export function orderableBusinessDays(count = 5): string[] {
  const days: string[] = [];
  let cursor = new Date();

  while (days.length < count) {
    const weekday = cursor.getDay();
    if (weekday !== 0 && weekday !== 6) days.push(localIsoDate(cursor));
    cursor = new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate() + 1);
  }

  return days;
}

export function formatOrderDate(date: string, long = false): string {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: long ? "long" : undefined,
    day: "2-digit",
    month: long ? "long" : "short",
  }).format(new Date(`${date}T12:00:00`));
}

export function createDemoOrders(currentCompany?: {
  id: string;
  name: string;
}): DemoOrder[] {
  const today = localIsoDate();
  const tomorrow = addCalendarDays(today, 1);
  const company = currentCompany ?? { id: "acme", name: "Acme Tecnologia" };

  return [
    {
      id: "demo-001",
      companyId: company.id,
      companyName: company.name,
      date: today,
      menuItemId: "frango-grelhado",
      menuItemName: "Frango grelhado",
      size: "M",
      employeeName: "Marina Costa",
      employeePhone: "11988776655",
      employeeDepartment: "Financeiro",
      employeeCpf: "12345678901",
      productionStatus: "pending",
      createdAt: `${today}T08:14:00-03:00`,
    },
    {
      id: "demo-002",
      companyId: company.id,
      companyName: company.name,
      date: today,
      menuItemId: "vegetariano",
      menuItemName: "Bowl vegetariano",
      size: "P",
      employeeName: "Rafael Nunes",
      employeePhone: "11977885544",
      employeeDepartment: "Produto",
      employeeCpf: "23456789012",
      productionStatus: "printed",
      createdAt: `${today}T08:21:00-03:00`,
    },
    {
      id: "demo-003",
      companyId: "deltha",
      companyName: "Deltha Contabilidade",
      date: today,
      menuItemId: "picadinho-carne",
      menuItemName: "Picadinho de carne",
      size: "G",
      employeeName: "Carlos Moreira",
      employeePhone: "11966774433",
      employeeDepartment: "Fiscal",
      employeeCpf: "34567890123",
      productionStatus: "separated",
      createdAt: `${today}T08:37:00-03:00`,
    },
    {
      id: "demo-004",
      companyId: "deltha",
      companyName: "Deltha Contabilidade",
      date: today,
      menuItemId: "frango-grelhado",
      menuItemName: "Frango grelhado",
      size: "M",
      employeeName: "Ana Beatriz",
      employeePhone: "11955663322",
      employeeDepartment: "Pessoal",
      employeeCpf: "45678901234",
      productionStatus: "pending",
      createdAt: `${today}T09:02:00-03:00`,
    },
    {
      id: "demo-005",
      companyId: "orbita",
      companyName: "Órbita Engenharia",
      date: today,
      menuItemId: "frango-grelhado",
      menuItemName: "Frango grelhado",
      size: "G",
      employeeName: "João Pedro Lima",
      employeePhone: "11944552211",
      employeeDepartment: "Obras",
      employeeCpf: "56789012345",
      productionStatus: "delivered",
      createdAt: `${today}T09:16:00-03:00`,
    },
    {
      id: "demo-006",
      companyId: company.id,
      companyName: company.name,
      date: tomorrow,
      menuItemId: "picadinho-carne",
      menuItemName: "Picadinho de carne",
      size: "M",
      employeeName: "Bianca Rocha",
      employeePhone: "11933441100",
      employeeDepartment: "Comercial",
      employeeCpf: "67890123456",
      productionStatus: "pending",
      createdAt: `${today}T09:24:00-03:00`,
    },
  ];
}

export function nextProductionStatus(
  current: ProductionStatus,
): ProductionStatus | null {
  const currentIndex = PRODUCTION_STATUS.findIndex((item) => item.value === current);
  return PRODUCTION_STATUS[currentIndex + 1]?.value ?? null;
}
