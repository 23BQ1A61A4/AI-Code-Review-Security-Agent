import java.sql.*;

public class UserService {

    private String dbPassword = "hardcoded-secret-pw";

    public ResultSet findUser(Connection conn, String username) throws SQLException {
        Statement stmt = conn.createStatement();
        String query = "SELECT * FROM users WHERE username = '" + username + "'";
        return stmt.executeQuery(query);
    }

    public void riskyOperation(String userInput) {
        try {
            Runtime.getRuntime().exec("ping " + userInput);
        } catch (Exception e) {
            // swallowed on purpose to demonstrate an empty catch block
        }
    }

    public void handleRequestWithManyParams(String a, String b, String c, String d,
                                             String e, String f, String g, String h) {
        System.out.println(a + b + c + d + e + f + g + h);
    }
}
