import api from "../api";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ACCESS_TOKEN, GOOGLE_ACCESS_TOKEN, REFRESH_TOKEN } from "../token";
import { useAuth } from "../auth";

const AuthForm = ({ route, method }) => {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const navigate = useNavigate();

    const { login, isAuthorized } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const response = await api.post(route, {
                username,
                password,
            });

            if (method === 'login') {
                localStorage.setItem(ACCESS_TOKEN, response.data.access_token);
                localStorage.setItem(REFRESH_TOKEN, response.data.refresh_token);
                navigate("/dashboard");
                window.location.reload();
            } else {
                setSuccess("Registration successful. Please login.");
                setTimeout(() => {
                    navigate("/signin");
                }, 2000);   
            }
        } catch (error) {
            console.error(error);
            if (error.response) {
                if (error.response.status === 401) {
                    setError("Invalid credentials.");
                } else if (error.response.status === 400) {
                    setError("Username already exists.");
                } else {
                    setError("An error occurred. Please try again.");
                }
            } else if (error.request) {
                setError("No response from server. Please check your network.");
            } else {
                setError("An error occurred. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleLogin = async () => {
        window.location.href = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/accounts/login` //Google Callback URL
    };

    useEffect(() => {
        const handleGoogleCallback = async () => {
            // Check if we are on the callback page
            if (window.location.pathname === "/google-callback") {
                // Extract the token from the URL
                const params = new URLSearchParams(window.location.search);
                const googleAccessToken = params.get("access_token");

                if (googleAccessToken) {
                    localStorage.setItem(GOOGLE_ACCESS_TOKEN, googleAccessToken);

                    // Validate the token through the AuthContext
                    await login({ google_token: googleAccessToken });
                    navigate("/dashboard", { replace: true });
                }
            }
        };

        handleGoogleCallback();
    }, [navigate, login]);
    
    return (
        <div className = "form-container">
            {loading && (
                <div className="loading-indicator">
                    {error ? <span className="error-message">{error}</span> : <div className="spinner"></div>}
                </div>
            )}
            {!loading && (
                <form onSubmit={handleSubmit}>
                    <h2>{method === 'login' ? 'Login' : 'Register'}</h2>
                    {error && <p className="error">{error}</p>}
                    {success && <p className="success">{success}</p>}
                    <div className="form-group">
                        <label htmlFor="username">Username:</label>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required />
                    </div>
                    <div className="form-group">
                        <label htmlFor="password">Password:</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required />
                    </div>
                    <button type="submit" className="btn btn-primary">
                        {method === 'register' ? 'Register' : 'Login'}
                    </button>
                    <button type="button" className="google-button" onClick={handleGoogleLogin}>
                        <img src="/path/to/google-icon.png" alt="Google Icon" />
                        {method === 'register' ? 'Register with Google' : 'Login with Google'}
                    </button>
                    {method === 'login' && (
                        <p className="toggle-text">Don't have an account?
                            <span className="toggle-link" onClick={() => navigate("/signup")}> Sign Up</span>
                        </p>
                    )}
                    {method === 'register' && (
                        <p className="toggle-text">Already have an account?
                            <span className="toggle-link" onClick={() => navigate("/signin")}> Login</span>
                        </p>
                    )}
                </form>
            )}
            {!loading && (
                <div className="google-login">
                    <button onClick={handleGoogleLogin}>Login with Google</button>
                </div>
            )}
        </div>

    );
};

export default AuthForm;