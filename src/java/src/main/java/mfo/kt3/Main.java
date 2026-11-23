package mfo.kt3;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class Main {
    private Main() {}

    public static void main(String[] args) {
        if (args.length != 2 || !"--data".equals(args[0])) {
            System.err.println("Usage: java -jar target/mfo-kt3.jar --data sample_data.json");
            System.exit(2);
        }
        try (InputStream input = Files.newInputStream(Path.of(args[1]))) {
            JsonCases json = new JsonCases();
            JsonCases.Case example = json.read(input);
            ReviewWorkflow.Result result = new ReviewWorkflow().review(example.input());
            String output = json.write(result, example.originalApplication()) + System.lineSeparator();
            System.out.write(output.getBytes(StandardCharsets.UTF_8));
        } catch (IOException | IllegalArgumentException error) {
            String message = error.getMessage() + System.lineSeparator();
            System.err.writeBytes(message.getBytes(StandardCharsets.UTF_8));
            System.exit(1);
        }
    }
}
