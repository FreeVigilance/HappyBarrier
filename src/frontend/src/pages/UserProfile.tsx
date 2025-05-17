import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FaSignOutAlt } from "react-icons/fa";

const UserProfile: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [name, setName] = useState("Загрузка...");
  const [phone, setPhone] = useState(() => location.state?.phone || "");
  const [isEditingName, setIsEditingName] = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [showSwitch, setShowSwitch] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const [accessToken, setAccessToken] = useState(
    () => location.state?.access_token || localStorage.getItem("access_token"),
  );
  const [refreshToken] = useState(
    () =>
      location.state?.refresh_token || localStorage.getItem("refresh_token"),
  );

  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        const meResponse = await fetch("/api/users/me/", {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            Accept: "application/json",
          },
        });

        if (meResponse.ok) {
          const userData = await meResponse.json();
          setName(userData.full_name || "Без имени");
          setPhone(userData.phone || "-");
          checkAdmin(userData.phone);
        } else {
          await refreshTokenAndRetry();
        }
      } catch (err) {
        console.error("Ошибка при получении профиля:", err);
        navigate("/login");
      }
    };

    const refreshTokenAndRetry = async () => {
      try {
        const refreshResponse = await fetch("/api/auth/token/refresh/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh: refreshToken }),
        });
        const refreshData = await refreshResponse.json();
        if (refreshResponse.ok && refreshData.access) {
          setAccessToken(refreshData.access);
          localStorage.setItem("access_token", refreshData.access);
          fetchUserProfile();
        } else {
          navigate("/login");
        }
      } catch {
        navigate("/login");
      }
    };

    const checkAdmin = async (userPhone: string) => {
      try {
        const res = await fetch("/api/users/check_admin/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ phone: userPhone }),
        });
        const data = await res.json();
        if (res.ok && data.is_admin) {
          setShowSwitch(true);
        }
      } catch (error) {
        console.error("Ошибка проверки админа", error);
      }
    };

    fetchUserProfile();
  }, [accessToken, refreshToken, navigate]);

  const handleSave = async () => {
    try {
      const patchResponse = await fetch("/api/users/me/", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ full_name: name, phone_privacy: "public" }),
      });

      if (patchResponse.ok) {
        setRequestSent(true);
        setTimeout(() => {
          setRequestSent(false);
          setIsEditingName(false);
        }, 2000);
      }
    } catch (error) {
      console.error("Ошибка при сохранении:", error);
    }
  };

  const navigateWithState = (path: string) => {
    navigate(path, {
      state: {
        phone,
        access_token: accessToken,
        refresh_token: refreshToken,
      },
    });
  };

  const handleRoleSwitch = () => {
    if (isAdmin) {
      navigate("/user", {
        state: {
          phone,
          access_token: accessToken,
          refresh_token: refreshToken,
        },
      });
    } else {
      navigate("/admin", {
        state: {
          phone,
          access_token: accessToken,
          refresh_token: refreshToken,
        },
      });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("phone");
    navigate("/login");
  };

  return (
    <div style={styles.container}>
      <div style={styles.logoutContainer}>
        <button
          onClick={handleLogout}
          style={styles.logoutButton}
          title="Выйти"
        >
          <FaSignOutAlt />
        </button>
      </div>

      <h2 style={styles.title}>Профиль</h2>

      <div style={styles.card}>
        {isEditingName ? (
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={styles.input}
          />
        ) : (
          <p style={styles.text}>{name || "—"}</p>
        )}
        <button
          style={styles.button}
          onClick={() => {
            isEditingName ? handleSave() : setIsEditingName(true);
          }}
        >
          {isEditingName
            ? requestSent
              ? "Сохранено"
              : "Сохранить"
            : "Изменить имя"}
        </button>
      </div>

      <div style={styles.card}>
        <p style={styles.text}>{phone || "—"}</p>
        <button
          style={styles.button}
          onClick={() => navigateWithState("/change-phone")}
        >
          Изменить телефон
        </button>
      </div>

      {showSwitch && (
        <div style={styles.switchBlock}>
          <span style={!isAdmin ? styles.activeText : styles.inactiveText}>
            Пользователь
          </span>
          <label style={styles.switch}>
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={() => {
                setIsAdmin((prev) => !prev);
                handleRoleSwitch();
              }}
              style={styles.switchInput}
            />
            <span
              style={{
                ...styles.slider,
                ...(isAdmin ? styles.switchChecked : {}),
              }}
            >
              <span
                style={{
                  ...styles.sliderBefore,
                  ...(isAdmin ? styles.switchCheckedBefore : {}),
                }}
              />
            </span>
          </label>
          <span style={isAdmin ? styles.activeText : styles.inactiveText}>
            Администратор
          </span>
        </div>
      )}

      <button
        style={{
          ...styles.deleteButton,
          backgroundColor: "#d9534f",
          marginTop: "10px",
        }}
        onClick={() =>
          navigate("/delete-account", {
            state: {
              phone,
              access_token: accessToken,
              refresh_token: refreshToken,
            },
          })
        }
      >
        Удалить профиль
      </button>

      <div style={styles.navbar}>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/barriers", {
              state: {
                phone,
                access_token: accessToken,
                refresh_token: refreshToken,
              },
            })
          }
        >
          Шлагбаумы
        </button>
        <button
          style={styles.navButton}
          onClick={() =>
            navigate("/requests", {
              state: {
                phone,
                access_token: accessToken,
                refresh_token: refreshToken,
              },
            })
          }
        >
          Запросы
        </button>
        <button style={{ ...styles.navButton, ...styles.navButtonActive }}>
          Профиль
        </button>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    width: "100vw",
    backgroundColor: "#fef7fb",
    color: "#333",
    padding: "20px",
  },
  logoutContainer: {
    alignSelf: "flex-end",
    marginBottom: "20px",
  },
  logoutButton: {
    background: "none",
    border: "none",
    fontSize: "25px",
    color: "#5a4478",
    cursor: "pointer",
    maxWidth: "100px",
  },
  deleteButton: {
    width: "100%",
    maxWidth: "420px",
    margin: "20px auto",
    backgroundColor: "#d9534f",
    color: "#fff",
    padding: "14px",
    borderRadius: "24px",
    border: "none",
    cursor: "pointer",
    fontWeight: "bold",
    fontSize: "16px",
    display: "block",
  },
  title: {
    fontSize: "24px",
    color: "#5a4478",
    marginBottom: "20px",
    fontWeight: "bold",
  },
  card: {
    backgroundColor: "#fff",
    padding: "15px",
    borderRadius: "10px",
    boxShadow: "0 4px 10px rgba(90, 68, 120, 0.15)",
    textAlign: "center",
    width: "90%",
    maxWidth: "400px",
    marginBottom: "20px",
  },
  text: {
    fontSize: "18px",
    marginBottom: "10px",
  },
  input: {
    width: "100%",
    padding: "10px",
    borderRadius: "8px",
    border: "1px solid #ccc",
    outline: "none",
    fontSize: "16px",
    marginBottom: "10px",
  },
  button: {
    width: "100%",
    padding: "10px 15px",
    backgroundColor: "#5a4478",
    color: "#fff",
    border: "none",
    borderRadius: "20px",
    fontSize: "14px",
    cursor: "pointer",
  },
  switchBlock: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginTop: "20px",
    gap: "10px",
  },
  switch: {
    position: "relative",
    display: "inline-block",
    width: "50px",
    height: "24px",
  },
  switchInput: {
    opacity: 0,
    width: 0,
    height: 0,
  },
  slider: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "#ccc",
    borderRadius: "24px",
    transition: ".4s",
  },
  sliderBefore: {
    content: "''",
    position: "absolute",
    height: "18px",
    width: "18px",
    left: "3px",
    bottom: "3px",
    backgroundColor: "white",
    borderRadius: "50%",
    transition: ".4s",
  },
  switchChecked: {
    backgroundColor: "#5a4478",
  },
  switchCheckedBefore: {
    transform: "translateX(26px)",
  },
  navbar: {
    display: "flex",
    justifyContent: "space-around",
    width: "100%",
    position: "fixed",
    bottom: 0,
    backgroundColor: "#f8f3fb",
    padding: "10px 0",
  },
  navButton: {
    background: "none",
    border: "none",
    fontSize: "14px",
    color: "#5a4478",
    fontWeight: "bold",
    cursor: "pointer",
  },
  navButtonActive: {
    borderBottom: "2px solid #5a4478",
    paddingBottom: "4px",
  },
  activeText: {
    color: "#5a4478",
    fontWeight: "bold",
  },
  inactiveText: {
    color: "#999",
  },
};

export default UserProfile;
