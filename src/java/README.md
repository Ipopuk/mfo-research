# КТ3. Прототип обработки заявки на Java

Для сборки нужны JDK 21 или новее и Apache Maven 3.8 или новее. Проект собирается с целевой версией Java 21. При первой сборке Maven загружает Jackson для чтения и записи JSON.

Из каталога `src/java` выполните:

```powershell
mvn package
java -jar target/mfo-kt3.jar --data sample_data.json
```

Пример содержит те же синтетические данные, что и `src/sample_data.json` в КТ2. Подтверждённые доходы составляют 80 000, действующие платежи — 12 000, предложенный ежемесячный платёж — 18 000. В результате `complete` имеет значение `true`, `payment_share_percent` равен `37.5`, `outcome` — `approved`, `sent` — `true`. Решение берётся из поля `employee_decision`, которое заполняет сотрудник.

Для проверки других ветвей измените копию примера и укажите её через `--data`. Удаление связи заявки со справкой о доходах даст `request_information`. При `sent: false` программа запишет попытку уведомления и вернёт `retry_notification`.

| Операция КТ2 | Метод Java |
|---|---|
| `check_request` | `CompletenessCheck.check` |
| `calculate_payment_load` | `PaymentLoadCalculator.calculate` |
| `record_decision` | `Application.recordDecision` |
| `record_notification` | `Decision.recordNotification` |

Граница прототипа совпадает с КТ2. Согласия и результаты предыдущих проверок читаются из набора данных. Решение по заявке и попытка доставки задаются во входном файле.
