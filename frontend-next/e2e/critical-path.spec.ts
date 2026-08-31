import { expect, test } from "@playwright/test";

import {
  calendarDaysOfWeek,
  todayInTimeZone,
  weekdayLabel,
} from "../src/lib/week";

import { ADMIN, COMPANY, DISH, signIn } from "./support";

const TIME_ZONE = process.env.APP_TIME_ZONE ?? "America/Sao_Paulo";
const WEEK = calendarDaysOfWeek(todayInTimeZone(TIME_ZONE));

/**
 * The critical path of CLAUDE.md §8. It grows one step per vertical slice;
 * this is the part covered by slice A (admin publishes the week's menu).
 */
test("admin cadastra empresa, prato e publica o cardápio da semana", async ({
  page,
}) => {
  await signIn(page, ADMIN);
  await expect(page).toHaveURL(/\/admin\/empresas$/);

  await test.step("cadastra a empresa e seu acesso", async () => {
    await page.getByLabel("Nome da empresa").fill(COMPANY.name);
    await page.getByLabel("E-mail de acesso").fill(COMPANY.email);
    await page.getByLabel("Senha de acesso").fill(COMPANY.password);
    await page.getByRole("button", { name: "Cadastrar empresa" }).click();

    await expect(page.getByRole("status")).toContainText(COMPANY.name);
    await expect(
      page.getByRole("listitem").filter({ hasText: COMPANY.name }),
    ).toContainText(COMPANY.email);
  });

  await test.step("cadastra um prato", async () => {
    await page.getByRole("link", { name: "Pratos" }).click();
    await page.getByLabel("Nome do prato").fill(DISH.name);
    await page.getByLabel("Descrição (opcional)").fill(DISH.description);
    await page.getByRole("button", { name: "Cadastrar prato" }).click();

    await expect(page.getByRole("status")).toContainText(DISH.name);
    await expect(
      page.getByRole("listitem").filter({ hasText: DISH.name }),
    ).toContainText("P · M · G");
  });

  await test.step("monta o cardápio de segunda a domingo", async () => {
    await page.getByRole("link", { name: "Cardápio da semana" }).click();

    for (const date of WEEK) {
      const day = page.getByRole("group", {
        name: new RegExp(weekdayLabel(date)),
      });
      await expect(page.getByTestId(`status-${date}`)).toHaveText(
        "Não publicado",
      );
      await day.getByLabel(DISH.name).check();
    }

    await page.getByRole("button", { name: "Salvar cardápio" }).click();
    await expect(page.getByRole("status")).toContainText("Cardápio salvo");
  });

  await test.step("publica a semana", async () => {
    await page.getByRole("button", { name: "Publicar semana" }).click();
    await expect(page.getByRole("status")).toContainText("Cardápio publicado");

    for (const date of WEEK) {
      await expect(page.getByTestId(`status-${date}`)).toHaveText("Publicado");
    }
  });
});
