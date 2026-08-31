import { formatOrderDate } from "@/lib/demo-orders";
import { formatMealTime } from "@/lib/orders";
import type { KitchenOrder } from "@/lib/types";

type ThermalPrintDocumentProps =
  | { type: "order"; order: KitchenOrder }
  | { type: "day"; orders: KitchenOrder[]; date: string };

const TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
});

function ReceiptOrder({ order, compact = false }: { order: KitchenOrder; compact?: boolean }) {
  return (
    <article className={compact ? "thermal-order thermal-order--compact" : "thermal-order"}>
      <div className="thermal-order__heading">
        <strong>Pedido #{order.order_number}</strong>
        <span>{TIME_FORMATTER.format(new Date(order.created_at))}</span>
      </div>
      <p className="thermal-order__employee">{order.employee_name}</p>
      <p>{order.company_name}</p>
      <p>{order.employee_department} · almoço {formatMealTime(order.scheduled_for)}</p>
      <div className="thermal-order__dish">
        {order.items.map((item) => (
          <div key={item.id}>
            <strong>{item.quantity}× {item.item_name} · tamanho {item.size}</strong>
            {item.notes ? (
              <p className="thermal-order__notes"><strong>OBS:</strong> {item.notes}</p>
            ) : null}
          </div>
        ))}
      </div>
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
          <p className="thermal-date">{formatOrderDate(props.order.date, true)} · {formatMealTime(props.order.scheduled_for)}</p>
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
