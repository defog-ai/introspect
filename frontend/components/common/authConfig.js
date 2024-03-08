import { PublicClientApplication } from "@azure/msal-browser";

export const msalConfig = {
  auth: {
    clientId: `${process.env.NEXT_PUBLIC_MSAL_CLIENT_ID}`,
    authority: `https://login.microsoftonline.com/${process.env.NEXT_PUBLIC_MSAL_TENANT_ID}`,
    redirectUri: `${process.env.NEXT_PUBLIC_MSAL_REDIRECT_URI}`,
  }
};

export const msalInstance = new PublicClientApplication(msalConfig);