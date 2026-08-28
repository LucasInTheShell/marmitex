import { formatOrderDate } from "@/lib/demo-orders";
import type { DemoOrder } from "@/lib/demo-orders";

type ThermalPrintDocumentProps =
  | { type: "order"; order: DemoOrder }
  | { type: "day"; orders: DemoOrder[]; date: string };

const TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
});

function orderNumber(order: DemoOrder) {
  const numeric = order.id.match(/\d+/)?.[0];
  return numeric ? numeric.padStart(3, "0") : order.id.slice(-6).toUpperCase();
}

function ReceiptOrder({ order, compact = false }: { order: DemoOrder; compact?: boolean }) {
  return (
    <article className={compact ? "thermal-order thermal-order--compact" : "thermal-order"}>
      <div className="thermal-order__heading">
        <strong>Pedido #{orderNumber(order)}</strong>
        <span>{TIME_FORMATTER.format(new Date(order.createdAt))}</span>
      </div>
      <p className="thermal-order__employee">{order.employeeName}</p>
      <p>{order.companyName}</p>
      <p>{order.employeeDepartment} · final {order.employeePhone.slice(-4)}</p>
      <div className="thermal-order__dish">
        <strong>{order.quantity}× {order.menuItemName}</strong>
        <strong>Tamanho {order.size}</strong>
      </div>
      {order.notes ? (
        <p className="thermal-order__notes"><strong>OBS:</strong> {order.notes}</p>
      ) : null}
    </article>
  );
}

export function ThermalPrintDocument(props: ThermalPrintDocumentProps) {
  return (
    <section className="thermal-print-document" aria-hidden="true">
      <header className="thermal-header">
        <strong>MAVI CONNECT</strong>
        <span>{props.type === "order" ? "COMANDA DE PRODUÇÃO" : "MAPA DE PRODUÇÃO"}</span>
      </header>

      {props.type === "order" ? (
        <>
          <p className="thermal-date">{formatOrderDate(props.order.date, true)}</p>
          <ReceiptOrder order={props.order} />
          <footer className="thermal-footer">Conferir itens antes de liberar</footer>
        </>
      ) : (
        <>
          <p className="thermal-date">{formatOrderDate(props.date, true)} · {props.orders.length} pedidos</p>
          {props.orders.map((order) => <ReceiptOrder key={order.id} order={order} compact />)}
          <footer className="thermal-footer">Fim do mapa de produção</footer>
        </>
      )}
    </section>
  );
}
