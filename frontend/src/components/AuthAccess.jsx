import React from "react";
import { Navigate } from "react-router-dom";
import { useAuthentication } from "../auth";

function ProtectedRoute({children}) {
    const { isAuthorized } = useAuthentication();

    if (isAuthorized === null) {
        return <div>Loading...</div>
    }
    if (
        isAuthorized &&
        (window.location.pathname === "/signin" || window.location.pathname === "/signup")
    ) {
        return <Navigate to="/dashboard" />;
    }

    return children;
}

export default ProtectedRoute;