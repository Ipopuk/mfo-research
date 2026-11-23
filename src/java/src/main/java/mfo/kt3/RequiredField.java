package mfo.kt3;

import java.util.Optional;

public record RequiredField(String entity, String field) implements CompletenessRule {
    @Override
    public Optional<Missing> inspect(CompletenessCheck.Input input) {
        Object value = input.fields().get(entity).get(field);
        if (value == null || "".equals(value) || Boolean.FALSE.equals(value)
            || (value instanceof Number number && number.doubleValue() <= 0)) {
            return Optional.of(new Missing(Category.FIELD, entity + "." + field));
        }
        return Optional.empty();
    }
}
