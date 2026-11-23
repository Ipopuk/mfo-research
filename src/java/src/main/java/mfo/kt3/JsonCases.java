package mfo.kt3;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

final class JsonCases {
    record Case(ReviewWorkflow.Input input, ObjectNode originalApplication) {}

    private final ObjectMapper mapper = new ObjectMapper()
        .enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS)
        .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);

    Case read(InputStream source) throws IOException {
        JsonNode root = mapper.readTree(source);
        if (root == null || !root.isObject()) {
            throw new IllegalArgumentException("Входной JSON должен содержать объект заявки");
        }
        JsonNode person = root.path("applicant");
        JsonNode request = root.path("application");
        if (!person.isObject() || !(request instanceof ObjectNode applicationJson)) {
            throw new IllegalArgumentException("Требуются объекты applicant и application");
        }
        Applicant applicant = new Applicant(text(person, "applicant_id"), text(person, "full_name"), text(person, "contact"));
        Application application = new Application(text(request, "application_id"), text(request, "applicant_id"),
            decimal(request, "amount"), integer(request, "term_months"), text(request, "status"), text(request, "received_at"));

        Map<String, Document> documents = new HashMap<>();
        for (JsonNode row : array(root, "documents")) {
            Document document = new Document(text(row, "document_id"), text(row, "kind"), row.path("valid").asBoolean());
            documents.put(document.id(), document);
        }
        List<ApplicationDocument> links = rows(root, "application_documents", row -> new ApplicationDocument(
            text(row, "application_id"), text(row, "document_id"), text(row, "received_at")));
        Map<String, Map<String, Object>> fields = Map.of("applicant", values(person), "application", values(request));
        CompletenessCheck.Input completeness = new CompletenessCheck.Input(application.id(), fields, documents, links);
        List<CompletenessRule> rules = new ArrayList<>();
        for (JsonNode pair : array(root, "required_fields")) {
            if (!pair.isArray() || pair.size() != 2 || !pair.get(0).isTextual() || !pair.get(1).isTextual()
                || !fields.containsKey(pair.get(0).textValue())) {
                throw new IllegalArgumentException("Каждый элемент required_fields должен содержать сущность и имя поля");
            }
            rules.add(new RequiredField(pair.get(0).textValue(), pair.get(1).textValue()));
        }
        for (JsonNode kind : array(root, "required_document_kinds")) {
            rules.add(new RequiredDocument(kind.asText()));
        }

        List<Income> incomes = rows(root, "incomes", row -> new Income(text(row, "income_id"),
            text(row, "applicant_id"), decimal(row, "monthly_amount"), row.path("verified").asBoolean()));
        List<Obligation> obligations = rows(root, "obligations", row -> new Obligation(text(row, "obligation_id"),
            text(row, "applicant_id"), decimal(row, "monthly_payment"), row.path("active").asBoolean()));
        List<Consent> consents = root.has("consents") ? rows(root, "consents", row -> new Consent(
            text(row, "consent_id"), text(row, "application_id"), text(row, "kind"), text(row, "status"),
            text(row, "granted_at"))) : List.of();
        List<CheckResult> checks = root.has("check_results") ? rows(root, "check_results", row -> new CheckResult(
            text(row, "check_id"), text(row, "application_id"), text(row, "kind"), text(row, "source"),
            text(row, "result"), text(row, "checked_at"))) : List.of();

        JsonNode choice = root.path("employee_decision");
        ReviewWorkflow.EmployeeChoice employee = choice.isObject() ? new ReviewWorkflow.EmployeeChoice(
            text(choice, "decision_id"), text(choice, "employee_id"), text(choice, "outcome"), text(choice, "reason"),
            decimal(choice, "approved_amount"), integer(choice, "approved_term_months")) : null;
        JsonNode notification = root.path("notification");
        ReviewWorkflow.NotificationAttempt attempt = notification.isObject() ? new ReviewWorkflow.NotificationAttempt(
            text(notification, "notification_id"), text(notification, "channel"), notification.path("sent").asBoolean()) : null;
        BigDecimal payment = decimal(root, "proposed_monthly_payment");
        if (payment == null) {
            throw new IllegalArgumentException("Требуется число proposed_monthly_payment");
        }
        return new Case(new ReviewWorkflow.Input(applicant, application, completeness, rules, incomes, obligations,
            consents, checks, payment, employee, attempt), applicationJson);
    }

    String write(ReviewWorkflow.Result review, ObjectNode original) throws IOException {
        ObjectNode result = mapper.createObjectNode();
        result.put("application_id", review.applicationId());
        ObjectNode completeness = result.putObject("completeness");
        completeness.put("complete", review.completeness().complete());
        completeness.set("missing_fields", mapper.valueToTree(review.completeness().missingFields()));
        completeness.set("missing_documents", mapper.valueToTree(review.completeness().missingDocuments()));
        ObjectNode load = result.putObject("payment_load");
        load.put("status", review.paymentLoad().status());
        load.put("monthly_income", review.paymentLoad().monthlyIncome());
        load.put("existing_payments", review.paymentLoad().existingPayments());
        load.put("payment_share_percent", review.paymentLoad().paymentSharePercent());

        if (review.decision() != null) {
            result.set("application", original.deepCopy().put("status", review.application().status()));
            Decision decision = review.decision();
            ObjectNode decisionOutput = result.putObject("decision");
            decisionOutput.put("decision_id", decision.id());
            decisionOutput.put("application_id", decision.applicationId());
            decisionOutput.put("employee_id", decision.employeeId());
            decisionOutput.put("outcome", decision.outcome());
            decisionOutput.put("reason", decision.reason());
            decisionOutput.put("approved_amount", decision.approvedAmount());
            decisionOutput.put("approved_term_months", decision.approvedTermMonths());

            Notification notification = review.notification();
            ObjectNode notificationOutput = result.putObject("notification");
            notificationOutput.put("notification_id", notification.id());
            notificationOutput.put("decision_id", notification.decisionId());
            notificationOutput.put("channel", notification.channel());
            notificationOutput.put("sent", notification.sent());
        }
        if (review.nextStep() != null) {
            result.put("next_step", review.nextStep());
        }
        return mapper.writerWithDefaultPrettyPrinter().writeValueAsString(result);
    }

    private Map<String, Object> values(JsonNode node) {
        return mapper.convertValue(node, new TypeReference<Map<String, Object>>() {});
    }

    private static <T> List<T> rows(JsonNode root, String name, Function<JsonNode, T> convert) {
        List<T> values = new ArrayList<>();
        for (JsonNode row : array(root, name)) {
            values.add(convert.apply(row));
        }
        return values;
    }

    private static JsonNode array(JsonNode root, String name) {
        JsonNode node = root.path(name);
        if (!node.isArray()) {
            throw new IllegalArgumentException("Требуется массив " + name);
        }
        return node;
    }

    private static String text(JsonNode node, String name) {
        return node.path(name).asText(null);
    }

    private static BigDecimal decimal(JsonNode node, String name) {
        JsonNode value = node.path(name);
        return value.isNumber() ? value.decimalValue() : null;
    }

    private static Integer integer(JsonNode node, String name) {
        JsonNode value = node.path(name);
        return value.isIntegralNumber() && value.canConvertToInt() ? value.intValue() : null;
    }
}
