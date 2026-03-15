export interface FormOptionItem {
  value: string;
  label?: string;
  labelKey?: string;
  canonicalLabel?: string;
  isDefault?: boolean;
  appliesTo?: string[];
}

export interface FormMetadataDefaults {
  searchType: string;
  situation: string;
  itemsPerPage: string;
}

export interface FormMetadata {
  version: number;
  updatedAt?: string;
  searchTypes: FormOptionItem[];
  situations: FormOptionItem[];
  itemsPerPage: FormOptionItem[];
  defaults: FormMetadataDefaults;
}
