import {useState, useEffect} from "react";
import {useAuth} from "../../auth/AuthContext";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import BunkCard from "../../components/bunklogs/BunkCard";

function BunkGrid() {
  const [error, setError] = useState(null);
  const { user, isAuthenticated, loading, logout } = useAuth();
  const navigate = useNavigate();
  const email = useAuth().user?.email;
  const [userData, setUserData] = useState(null);
  const [fetchingUserData, setFetchingUserData] = useState(false);

  // Fetch user data from API
    useEffect(() => {
      const fetchUserData = async () => {
        if (email) {
          setFetchingUserData(true);
          try {
            const response = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/users/email/${email}`);
            setUserData(response.data);
          } catch (err) {
            setError(err.response?.data?.message || 'Failed to fetch user data');
            console.error('Error fetching user data:', err);
          } finally {
            setFetchingUserData(false);
          }
        }
      };
      
      fetchUserData();
    }, [email, setError]);

  return (
    <div className="grid grid-cols-12 gap-6">
        {userData && userData.bunks.map((bunk) => (
            <BunkCard
            key={bunk.id}
            cabin={bunk.cabin}
            session={bunk.session}
            bunk_id={bunk.id}
            counselors={bunk.counselors}
            />
        ))}
    </div>
  );
}
export default BunkGrid;