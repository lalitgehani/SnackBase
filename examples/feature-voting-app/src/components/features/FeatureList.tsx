/**
 * Feature list page
 * Displays all features with voting functionality
 */

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useAuth, useSnackBase } from '@snackbase/sdk/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LogOut, Plus, ThumbsUp, BarChart3, TrendingUp } from 'lucide-react'
import type { Feature } from '@/types'

export default function FeatureList() {
  const { user, logout } = useAuth()
  const client = useSnackBase()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [sortBy, setSortBy] = useState<'recent' | 'votes'>('votes')
  const [localFeatures, setLocalFeatures] = useState<Feature[]>([])

  // Fetch features using SDK
  const { data, loading, refetch } = useQuery<Feature>('features', {
    sort: sortBy === 'votes' ? '-votes' : '-created_at',
  })

  // Mutation for creating features
  const { create: createFeature, loading: creating } = useMutation<Feature>('features')

  // Update local features when data changes
  useEffect(() => {
    if (data?.items) {
      // Parse voted_by if it's a string from the API
      const parsedFeatures = data.items.map((f: Feature) => {
        if (f.voted_by && typeof f.voted_by === 'string') {
          return { ...f, voted_by: JSON.parse(f.voted_by) }
        }
        return f
      })
      setLocalFeatures(parsedFeatures)
    }
  }, [data])

  // Subscribe to real-time updates
  useEffect(() => {
    // Listen for message events (returns unsubscribe function)
    const unsubscribe = client.realtime.on('message', (message: any) => {
      // Message format: { type: 'features.create', data: { record, action } }
      if (message.type && message.type.startsWith('features.')) {
        const record = message.data?.record
        const action = message.data?.action || message.type.split('.')[1]

        if (action === 'create' && record) {
          setLocalFeatures((prev) => [record as Feature, ...prev])
        } else if (action === 'update' && record) {
          setLocalFeatures((prev) =>
            prev.map((f) => {
              if (f.id === record.id) {
                const updated = record as Feature
                // Parse voted_by if it's a string from the API
                if (updated.voted_by && typeof updated.voted_by === 'string') {
                  return { ...updated, voted_by: JSON.parse(updated.voted_by) }
                }
                return updated
              }
              return f
            })
          )
        } else if (action === 'delete' && record) {
          setLocalFeatures((prev) => prev.filter((f) => f.id !== record.id))
        }
      }
    })

    // Subscribe to the features collection
    client.realtime.subscribe('features', ['create', 'update', 'delete'])

    return () => {
      unsubscribe()
      client.realtime.unsubscribe('features')
    }
  }, [client])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !description.trim()) return

    try {
      const newFeature = await createFeature({
        title,
        description,
        votes: 0,
        status: 'open',
        voted_by: [],
      })
      setLocalFeatures((prev) => [newFeature as Feature, ...prev])
      setTitle('')
      setDescription('')
      setShowForm(false)
    } catch (error) {
      console.error('Failed to create feature:', error)
    }
  }

  const handleVote = async (feature: Feature) => {
    if (!user) return

    // Parse voted_by - handle both string (from API) and array cases
    const votedBy = feature.voted_by
      ? (typeof feature.voted_by === 'string' ? JSON.parse(feature.voted_by) : feature.voted_by) as string[]
      : []
    const hasVoted = votedBy.includes(user.id)

    try {
      const updatedVotes = hasVoted ? feature.votes - 1 : feature.votes + 1
      const updatedVotedBy = hasVoted
        ? votedBy.filter((id) => id !== user.id)
        : [...votedBy, user.id]

      await client.records.patch('features', feature.id, {
        votes: updatedVotes,
        voted_by: updatedVotedBy,
      })

      // Update local state
      setLocalFeatures((prev) =>
        prev.map((f) =>
          f.id === feature.id
            ? { ...f, votes: updatedVotes, voted_by: updatedVotedBy }
            : f
        )
      )
    } catch (error) {
      console.error('Failed to vote:', error)
    }
  }

  const handleStatusChange = async (featureId: string, newStatus: Feature['status']) => {
    try {
      await client.records.patch('features', featureId, { status: newStatus })
      setLocalFeatures((prev) =>
        prev.map((f) => (f.id === featureId ? { ...f, status: newStatus } : f))
      )
    } catch (error) {
      console.error('Failed to update status:', error)
    }
  }

  const handleDelete = async (featureId: string) => {
    try {
      await client.records.delete('features', featureId)
      setLocalFeatures((prev) => prev.filter((f) => f.id !== featureId))
    } catch (error) {
      console.error('Failed to delete feature:', error)
    }
  }

  const getStatusColor = (status: Feature['status']) => {
    switch (status) {
      case 'open':
        return 'bg-blue-100 text-blue-800'
      case 'in-progress':
        return 'bg-yellow-100 text-yellow-800'
      case 'completed':
        return 'bg-green-100 text-green-800'
    }
  }

  const getStatusLabel = (status: Feature['status']) => {
    switch (status) {
      case 'open':
        return 'Open'
      case 'in-progress':
        return 'In Progress'
      case 'completed':
        return 'Completed'
    }
  }

  const hasVoted = (feature: Feature) => {
    if (!user || !feature.voted_by) return false
    // Parse voted_by if it's a string from the API
    const votedBy = typeof feature.voted_by === 'string' ? JSON.parse(feature.voted_by) : feature.voted_by
    return votedBy.includes(user.id)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <BarChart3 className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Feature Voting</h1>
                <p className="text-sm text-gray-600">Submit and vote on features</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">{user?.name || user?.email}</span>
              <Button onClick={logout} variant="outline" size="sm">
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <Button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            {showForm ? 'Cancel' : 'New Feature'}
          </Button>

          <div className="flex items-center gap-2 ml-auto">
            <span className="text-sm text-gray-600">Sort by:</span>
            <Button
              variant={sortBy === 'votes' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSortBy('votes')}
            >
              <TrendingUp className="h-4 w-4 mr-1" />
              Votes
            </Button>
            <Button
              variant={sortBy === 'recent' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSortBy('recent')}
            >
              Recent
            </Button>
          </div>
        </div>

        {/* New feature form */}
        {showForm && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Submit a New Feature</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    placeholder="Brief summary of the feature"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <textarea
                    id="description"
                    placeholder="Detailed description of the feature..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                    rows={4}
                    className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 min-h-[100px] resize-y"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={creating}>
                    {creating ? 'Submitting...' : 'Submit Feature'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Features list */}
        {loading && localFeatures.length === 0 ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
            <p className="mt-4 text-gray-600">Loading features...</p>
          </div>
        ) : localFeatures.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-600 mb-4">No features yet. Be the first to submit one!</p>
              <Button onClick={() => setShowForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Submit Feature
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {localFeatures.map((feature) => (
              <Card key={feature.id}>
                <CardContent className="p-6">
                  <div className="flex gap-4">
                    {/* Vote button */}
                    <button
                      onClick={() => handleVote(feature)}
                      disabled={!user}
                      className={cn(
                        "flex flex-col items-center gap-1 p-3 rounded-lg transition-colors min-w-[70px]",
                        hasVoted(feature)
                          ? "bg-blue-100 text-blue-700"
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      )}
                    >
                      <ThumbsUp className="h-5 w-5" />
                      <span className="text-lg font-bold">{feature.votes}</span>
                      <span className="text-xs">votes</span>
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{feature.title}</h3>
                        <span className={cn("px-2 py-1 rounded-full text-xs font-medium", getStatusColor(feature.status))}>
                          {getStatusLabel(feature.status)}
                        </span>
                      </div>
                      <p className="text-gray-600 mb-4">{feature.description}</p>

                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">
                          {new Date(feature.created_at).toLocaleDateString()}
                        </span>

                        {/* Status controls (for creators/admin) */}
                        {user && feature.created_by === user.id && (
                          <div className="flex items-center gap-2">
                            <select
                              value={feature.status}
                              onChange={(e) => handleStatusChange(feature.id, e.target.value as Feature['status'])}
                              className="text-sm border border-gray-300 rounded-md px-2 py-1"
                            >
                              <option value="open">Open</option>
                              <option value="in-progress">In Progress</option>
                              <option value="completed">Completed</option>
                            </select>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(feature.id)}
                              className="text-red-600 hover:text-red-700"
                            >
                              Delete
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ')
}
