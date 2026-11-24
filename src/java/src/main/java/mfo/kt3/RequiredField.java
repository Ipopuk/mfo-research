package mfo.kt3;

import java.util.Optional;

public record RequiredField(String entity, String field) implements CompletenessRule {
    @Override
    public Optional<Missing> inspect(CompletenessCheck.Input input) {
        Object value = input.fields().get(entity).get(field);
        // Match Python str.strip(), including non-breaking spaces and Unicode NEL.
        boolean blankText = value instanceof String text && text.codePoints().allMatch(codePoint ->
            Character.isWhitespace(codePoint) || Character.isSpaceChar(codePoint) || codePoint == 0x85);
        if (value == null || blankText || Boolean.FALSE.equals(value)
            || (value instanceof Number number && number.doubleValue() <= 0)) {
            return Optional.of(new Missing(Category.FIELD, entity + "." + field));
        }
        return Optional.empty();
    }
}
