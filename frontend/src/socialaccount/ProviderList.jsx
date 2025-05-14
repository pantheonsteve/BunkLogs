import { useConfig } from '../auth/hooks'
import { redirectToProvider, Client, settings } from '../lib/allauth'
import Button from '../components/Button'

export default function ProviderList(props) {
  const config = useConfig()
  const providers = config.data.socialaccount.providers
  if (!providers.length) {
    return null
  }
  return (
    <ul>
      {providers.map(provider => (
        <li key={provider.id}>
          <Button onClick={() => redirectToProvider(provider.id, props.callbackURL, props.process)}>
            {provider.name}
          </Button>
        </li>
      ))}
    </ul>
  )
}