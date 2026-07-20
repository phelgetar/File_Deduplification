 -- How many images analyzed?
  SELECT COUNT(*) FROM image_metadata;

  -- What tags were found?
  SELECT keyword, COUNT(*) as count
  FROM image_keywords
  GROUP BY keyword
  ORDER BY count DESC
  LIMIT 20;

  -- Forest photos from Ohio (your example)
  SELECT f.path, GROUP_CONCAT(ik.keyword) as tags
  FROM files f
  JOIN image_metadata im ON f.id = im.file_id
  JOIN image_keywords ik ON im.id = ik.image_metadata_id
  WHERE ik.keyword IN ('forest', 'Ohio')
  GROUP BY f.path;