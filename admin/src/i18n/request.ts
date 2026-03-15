import { getRequestConfig } from "next-intl/server";

import { defaultLocale } from "./config";
import { flatToNested } from "./flat-to-nested";

export default getRequestConfig(async () => {
  const locale = defaultLocale;
  const raw = (await import(`../../public/locales/${locale}.json`)).default;

  return {
    locale,
    messages: flatToNested(raw),
  };
});
