import React, { useState } from 'react';

const SSOButton = ({ msalInstance }) => {
  const [isLoginInProgress, setIsLoginInProgress] = useState(false);
  
  const handleLogin = async () => {
    if (isLoginInProgress) {
      return;
    }

    setIsLoginInProgress(true);
    try {
      // Login via a popup
      const loginResponse = await msalInstance.loginPopup({
        scopes: ["user.read"] // Replace with the scopes you need
      });

      const userEmail = loginResponse?.account?.username;
      const idToken = loginResponse?.idToken;

      // Handle post-login actions
      console.log("Login successful!");
      // send the user's email and id token to the server
      // if successful, save the token to local storage
    } catch (error) {
      console.error(error);
    }
  };

  console.log(msalInstance);

  return (
    <button onClick={handleLogin}>Sign In with Microsoft</button>
  );
};

export default SSOButton;
