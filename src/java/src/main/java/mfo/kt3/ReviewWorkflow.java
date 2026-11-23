package mfo.kt3;

import java.math.BigDecimal;
import java.util.List;
import java.util.Objects;

public final class ReviewWorkflow {
    public record EmployeeChoice(String id, String employeeId, String outcome, String reason,
                                 BigDecimal amount, Integer termMonths) {}

    public record NotificationAttempt(String id, String channel, boolean sent) {}

    public record Input(Applicant applicant, Application application,
                        CompletenessCheck.Input completenessInput, List<CompletenessRule> rules,
                        List<Income> incomes, List<Obligation> obligations,
                        List<Consent> consents, List<CheckResult> previousChecks,
                        BigDecimal proposedPayment, EmployeeChoice employeeChoice,
                        NotificationAttempt notificationAttempt) {}

    public record Result(String applicationId, CompletenessCheck.Result completeness,
                         PaymentLoadCalculator.Result paymentLoad, Application application,
                         Decision decision, Notification notification, String nextStep) {}

    private final CompletenessCheck completenessCheck = new CompletenessCheck();
    private final PaymentLoadCalculator paymentCalculator = new PaymentLoadCalculator();

    public Result review(Input input) {
        Application application = input.application();
        if (!Objects.equals(application.applicantId(), input.applicant().id())) {
            throw new IllegalArgumentException("Заявка связана с другим заявителем");
        }
        CompletenessCheck.Result completeness = completenessCheck.check(input.completenessInput(), input.rules());
        PaymentLoadCalculator.Result load = paymentCalculator.calculate(input.applicant(), input.incomes(),
            input.obligations(), input.proposedPayment());
        if (!completeness.complete() || !load.calculated()) {
            return new Result(application.id(), completeness, load, null, null, null, "request_information");
        }

        EmployeeChoice choice = input.employeeChoice();
        if (choice == null) {
            throw new IllegalArgumentException("В JSON отсутствует решение сотрудника");
        }
        Application.DecisionEntry entry = application.recordDecision(choice.id(), choice.employeeId(),
            choice.outcome(), choice.reason(), choice.amount(), choice.termMonths());
        NotificationAttempt attempt = input.notificationAttempt();
        if (attempt == null) {
            throw new IllegalArgumentException("В JSON отсутствует попытка уведомления");
        }
        Notification notification = entry.decision().recordNotification(attempt.id(), attempt.channel(), attempt.sent());
        String nextStep = notification.sent() ? null : "retry_notification";
        return new Result(application.id(), completeness, load, entry.application(), entry.decision(), notification, nextStep);
    }
}
